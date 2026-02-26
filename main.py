import os
import sys
import glob
import mmap
import json
import codecs
import shutil
from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tqdm import tqdm
import uuid
from methods.deduplicate import deduplicate
from methods.deduplicate.deduplicate_mt import parallel_deduplicate
from methods.jaccardsimilarity_deduplication import jaccard_deduplicate
from methods.fix_newlines import fix_newlines_doc
from methods.encoder.fixer import encoding_fixer
from methods.formatter import main as formatter
from methods import subprocesses
from methods.containers import apertium_pt_gl
from methods.normalize import extract_rules, process_file
from methods.subprocesses import mt_quelingua
from cli import build_parser

file_dir = os.path.dirname(os.path.abspath(__file__))
NUM_FILES = 6
TEMP_DIR = f"{file_dir}/temp_{os.getpid()}_{uuid.uuid4().hex[:8]}"

# --- Execution Handlers ---

def handle_mt_quelingua(args):
    #mt_quelingua(args.path, args.target, args.oujtput_tag, args.mode, args.field)
    mt_quelingua(args)
    sys.exit()

def handle_mt_transliteration(args):
    apertium_pt_gl(args.path, args.output, args.quelingua, args.mode, args.field)
    sys.exit()

def handle_formatter(args):
    args.delimiter = codecs.decode(args.delimiter, 'unicode_escape')
    formatter.run(args.path, args.technique, args.output, args.delimiter)
    sys.exit()

def handle_recoglang(args):
    print(subprocesses.quelingua(text=args.path, _type="whole"))
    sys.exit()

def handle_fix_newlines(args):
    fix_newlines_doc(path=args.path)
    sys.exit()

def handle_jaccard(args):
    jaccard_deduplicate(args)
    sys.exit()

def handle_deduplication(args):
    if args.type == "jaccard":
        jaccard_deduplicate.run(args)
    elif args.type == "simple":
        deduplicate.run(args)

def handle_mt_deduplication(args):
    parallel_deduplicate(file_to_process=args.source, parallel_file=args.target, file_type=args.mode, field=args.field)
    sys.exit()

def handle_normalizer(args):
    process_file(input_file=args.path, sheets=extract_rules(f"{file_dir}/data/normalization.xlsx"), 
                    detokenize=args.detokenize, output=args.output, 
                    mode=args.mode, jsonl_field=args.jsonl_field, bel=args.bel, exact=args.exact)
    sys.exit()
def handle_pipeline_task(args):
    if args.mode == "txt":
        extension = ".txt"
    elif args.mode == "jsonl":
        extension = ".jsonl"
    else:
        raise ValueError("Unsupported mode. Use 'txt' or 'jsonl'.")

    _split_into_files(args=args, num_files=NUM_FILES, extension=extension)
    files = glob.glob(f"{TEMP_DIR}/*{extension}")

    processes = [Process(target=parallelize, args=(f, args)) for f in files]
    for p in processes: p.start()
    for p in processes: p.join()

    if hasattr(args, "output") and args.output:
        with open(args.output, "w+", encoding="utf-8", errors="ignore") as tgt_file:
            sorted_files = sorted(files, key=lambda x: int(x.split("/")[-1].split(".")[0]))
            for file in sorted_files:
                if os.path.exists(f"{file}_p"):
                    with open(f"{file}_p", "r", encoding="utf-8") as fp:
                        shutil.copyfileobj(fp, tgt_file)


def convert_to_lf(input_file):
    out_path = f"{input_file}_lf"
    with open(input_file, "rb") as f_in, open(out_path, "wb") as f_out:
        for line in f_in:
            f_out.write(line.replace(b"\r\n", b"\n"))
    return out_path

def split_file_chunk(mm, start, lines_to_write, output_file, pbar, extension):
    with open(output_file, "wb") as out:
        for _ in range(lines_to_write):
            line = mm.readline()
            if not line: break
            if extension == ".jsonl":
                data = json.loads(line, strict=False)
                out.write(json.dumps(data, ensure_ascii=False).encode("utf-8") + b"\n")
            else:
                out.write(line)
            pbar.update(1)
        return mm.tell()

def _split_into_files(args, num_files, extension):
    Path(f"{TEMP_DIR}").mkdir(parents=True, exist_ok=True)
    with open(args.path, "r", encoding="utf-8", errors="ignore") as f:
        total_lines = sum(1 for _ in f)
    
    lpf = total_lines // num_files
    rem = total_lines % num_files
    
    with open(args.path, "r", encoding="utf-8", errors="ignore") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            start = 0
            with ThreadPoolExecutor() as ex:
                pbar = tqdm(total=total_lines, desc="Splitting")
                for i in range(num_files):
                    count = lpf + (1 if i < rem else 0)
                    out = f"{TEMP_DIR}/{i}{extension}"
                    start = ex.submit(split_file_chunk, mm, start, count, out, pbar, extension).result()
                pbar.close()

def parallelize(file, args):
    action = args.action
    if action == "mt_transliteration":
        apertium_pt_gl(file, f"{file}_p", args.quelingua, args.mode, args.field)
    else:  
        with open(f"{file}_p", "w", encoding="utf-8") as prd, open(file, "rb") as f:
            m_m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            for line_b in iter(m_m.readline, b""):
                line = line_b.decode("utf-8")
                if action == "tokenizer": line = subprocesses.tokenizer_paulo(line)
                elif action == "detokenizer": line = subprocesses.detokenizer_paulo(line)
                elif action == "encoder":
                    line = encoding_fixer(text=line, filtered_categories=args.categories, emojies=args.emojies)
                prd.write(f"{line}\n")
            m_m.close()

# --- Main Entry Point ---

def run():
    # Map actions to their handler functions
    handlers = {
        'formatter': handle_formatter,
        'recoglang': handle_recoglang,
        'fix_newlines': handle_fix_newlines,
        'jaccard': handle_jaccard,
        'deduplication': handle_deduplication,
        'pipeline': handle_pipeline_task,
        'mt_deduplication': handle_mt_deduplication,
        'normalize': handle_normalizer,
        'mt_quelingua': handle_mt_quelingua
        #'mt_transliteration': handle_mt_transliteration,
    }
    try:
        parser = build_parser(handlers)
        args = parser.parse_args()

        if not args.action:
            parser.print_help()
            return

        if os.path.exists(f"{file_dir}/temp"): shutil.rmtree(f"{file_dir}/temp")
        if args.eol: args.path = convert_to_lf(args.path)

        # Execute the handler associated with the sub-command
        if hasattr(args, "func"):
            args.func(args)

    # Cleanup
    finally:
        if os.path.exists(f"{TEMP_DIR}"): shutil.rmtree(f"{TEMP_DIR}")
        for f in os.listdir(file_dir):
            if f.startswith("__tmp_"): os.remove(f"{file_dir}/{f}")

if __name__ == "__main__":
    run()