import os
import sys
import glob
import mmap
import json
import codecs
import shutil
import argparse
from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tqdm import tqdm
import uuid
from typing import Any, List, Dict, Optional, Union
from methods.deduplicate import deduplicate
from methods.deduplicate.deduplicate_mt import parallel_deduplicate
from methods.jaccardsimilarity_deduplication import jaccard_deduplicate
from methods.fix_newlines import fix_newlines_doc
from methods.encoder.fixer import encoding_fixer
from methods.formatter import main as formatter
from methods import subprocesses
from methods.containers import apertium_pt_gl
from methods.mt_alignment import run_mt_alignment
from methods.normalize import extract_rules, process_file
from methods.subprocesses import mt_quelingua
from methods.galician_filter import filter_galician
from cli import build_parser

file_dir = os.path.dirname(os.path.abspath(__file__))
NUM_FILES = 6
TEMP_DIR = f"{file_dir}/temp_{os.getpid()}_{uuid.uuid4().hex[:8]}"

# --- Execution Handlers ---

def handle_mt_quelingua(args: argparse.Namespace) -> None:
    #mt_quelingua(args.path, args.target, args.oujtput_tag, args.mode, args.field)
    mt_quelingua(args)
    sys.exit()

def handle_mt_transliteration(args: argparse.Namespace) -> None:
    apertium_pt_gl(args.path, args.output, args.quelingua, args.mode, args.field)
    sys.exit()

def handle_formatter(args: argparse.Namespace) -> None:
    args.delimiter = codecs.decode(args.delimiter, 'unicode_escape')
    formatter.run(args.path, args.technique, args.output, args.delimiter)
    sys.exit()

def handle_recoglang(args: argparse.Namespace) -> None:
    print(subprocesses.quelingua(text=args.path, _type="whole"))
    sys.exit()

def handle_fix_newlines(args: argparse.Namespace) -> None:
    fix_newlines_doc(path=args.path)
    sys.exit()

def handle_jaccard(args: argparse.Namespace) -> None:
    jaccard_deduplicate(args)
    sys.exit()

def handle_deduplication(args: argparse.Namespace) -> None:
    if args.type == "jaccard":
        jaccard_deduplicate(args)
    elif args.type == "simple":
        deduplicate.run(args)

def handle_mt_deduplication(args: argparse.Namespace) -> None:
    parallel_deduplicate(file_to_process=args.source, parallel_file=args.target, file_type=args.mode, field=args.field)
    sys.exit()

def handle_mt_alignment(args: argparse.Namespace) -> None:
    run_mt_alignment(args)
    sys.exit()

def handle_normalizer(args: argparse.Namespace) -> None:
    process_file(input_file=args.path, sheets=extract_rules(f"{file_dir}/data/normalization.xlsx",  bel=args.bel, exact=args.exact), 
                    detokenize=args.detokenize, output=args.output, 
                    mode=args.mode, jsonl_field=args.jsonl_field)
    sys.exit()

def handle_pipeline_task(args: argparse.Namespace) -> None:
    if args.mode == "txt":
        extension = ".txt"
    elif args.mode == "jsonl":
        extension = ".jsonl"
    else:
        raise ValueError("Unsupported mode. Use 'txt' or 'jsonl'.")

    num_workers = getattr(args, 'workers', NUM_FILES)

    # Pre-load heavy models before forking so workers inherit via copy-on-write
    if args.action == "pyplexity":
        subprocesses.load_pyplexity_model(args.path_model)

    _split_into_files(args=args, num_files=num_workers, extension=extension)
    files = glob.glob(f"{TEMP_DIR}/*{extension}")
    # Don't grab the parallel files in the main list
    files = [f for f in files if "par_" not in os.path.basename(f)]

    processes = [Process(target=parallelize, args=(f, args)) for f in files]
    for p in processes: p.start()
    for p in processes: p.join()

    if hasattr(args, "output") and args.output:
        with open(args.output, "w+", encoding="utf-8", errors="ignore") as tgt_file:
            sorted_files = sorted(files, key=lambda x: int(os.path.basename(x).split(".")[0]))
            for file in sorted_files:
                if os.path.exists(f"{file}_p"):
                    with open(f"{file}_p", "r", encoding="utf-8") as fp:
                        shutil.copyfileobj(fp, tgt_file)
                        
    # Concatenate parallel output files if specified
    if hasattr(args, "parallel_output") and args.parallel_output:
        with open(args.parallel_output, "w+", encoding="utf-8", errors="ignore") as tgt_par_file:
            sorted_files = sorted(files, key=lambda x: int(os.path.basename(x).split(".")[0]))
            for file in sorted_files:
                par_file = f"{os.path.dirname(file)}/par_{os.path.basename(file)}"
                if os.path.exists(f"{par_file}_p"):
                    with open(f"{par_file}_p", "r", encoding="utf-8") as fp:
                        shutil.copyfileobj(fp, tgt_par_file)


def convert_to_lf(input_file: str) -> str:
    out_path = f"{input_file}_lf"
    with open(input_file, "rb") as f_in, open(out_path, "wb") as f_out:
        for line in f_in:
            f_out.write(line.replace(b"\r\n", b"\n"))
    return out_path

def split_file_chunk(mm: mmap.mmap, start: int, lines_to_write: int, output_file: str, pbar: Any, extension: str) -> int:
    with open(output_file, "wb") as out:
        for _ in range(lines_to_write):
            line = mm.readline()
            if not line: break
            if extension == ".jsonl":
                try:
                    data = json.loads(line, strict=False)
                    out.write(json.dumps(data, ensure_ascii=False).encode("utf-8") + b"\n")
                except json.JSONDecodeError:
                     out.write(line)
            else:
                out.write(line)
            pbar.update(1)
        return mm.tell()

def _split_into_files(args: argparse.Namespace, num_files: int, extension: str) -> None:
    Path(f"{TEMP_DIR}").mkdir(parents=True, exist_ok=True)
    with open(args.path, "r", encoding="utf-8", errors="ignore") as f:
        total_lines = sum(1 for _ in f)
    
    lpf = total_lines // num_files
    rem = total_lines % num_files
    
    has_parallel = hasattr(args, "parallel_file") and args.parallel_file is not None

    if os.path.getsize(args.path) == 0:
        return # Nothing to split
    with open(args.path, "r", encoding="utf-8", errors="ignore") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            start = 0
            with ThreadPoolExecutor() as ex:
                pbar = tqdm(total=total_lines, desc="Splitting Main File")
                for i in range(num_files):
                    count = lpf + (1 if i < rem else 0)
                    out = f"{TEMP_DIR}/{i}{extension}"
                    start = ex.submit(split_file_chunk, mm, start, count, out, pbar, extension).result()
                pbar.close()

    if has_parallel:
        with open(args.parallel_file, "r", encoding="utf-8", errors="ignore") as f_par:
            with mmap.mmap(f_par.fileno(), 0, access=mmap.ACCESS_READ) as mm_par:
                start_par = 0
                with ThreadPoolExecutor() as ex:
                    pbar_par = tqdm(total=total_lines, desc="Splitting Parallel File")
                    for i in range(num_files):
                        count = lpf + (1 if i < rem else 0)
                        out_par = f"{TEMP_DIR}/par_{i}{extension}"
                        start_par = ex.submit(split_file_chunk, mm_par, start_par, count, out_par, pbar_par, extension).result()
                    pbar_par.close()

def parallelize(file: str, args: argparse.Namespace) -> None:
    action = args.action
    if action == "mt_transliteration":
        apertium_pt_gl(file, f"{file}_p", args.quelingua, args.mode, args.field)
    elif action == "pyplexity":
        par_file = f"{os.path.dirname(file)}/par_{os.path.basename(file)}" if hasattr(args, "parallel_file") and args.parallel_file else None
        subprocesses.pyplexity(file, args, par_file)
    elif action == "filter_lang":
        par_file = f"{os.path.dirname(file)}/par_{os.path.basename(file)}" if hasattr(args, "parallel_file") and args.parallel_file else None
        subprocesses.quelingua_lines(file, args, par_file)
    elif action == "fasttext_gl":
        par_file = f"{os.path.dirname(file)}/par_{os.path.basename(file)}" if hasattr(args, "parallel_file") and args.parallel_file else None
        par_out = f"{par_file}_p" if par_file else None
        filter_galician(file, mode=args.mode, threshold=args.threshold, top_k=args.top_k, text_field=args.field, parallel_file=par_file, output_path=f"{file}_p", parallel_output_path=par_out)
    else:
        if os.path.getsize(file) == 0:
            return # Skip empty files
        with open(f"{file}_p", "w", encoding="utf-8") as prd, open(file, "rb") as f:
            if action in ["tokenizer", "detokenizer", "encoder"]:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m_m:
                    for line_b in iter(m_m.readline, b""):
                        line = line_b.decode("utf-8")
                        if not line: continue
                        if args.mode == "jsonl" and action == "encoder":
                            stripped = line.strip()
                            if not stripped:
                                prd.write(line)
                                continue
                            try:
                                data = json.loads(stripped)
                                field_to_fix = args.field if args.field else "text"
                                if field_to_fix in data:
                                    data[field_to_fix] = encoding_fixer(text=data[field_to_fix], filtered_categories=args.categories, emojies=args.emojies)
                                line = json.dumps(data, ensure_ascii=False) + "\n"
                            except json.JSONDecodeError:
                                # If not valid JSON, fallback to standard encoder on the whole line
                                line = encoding_fixer(text=line, filtered_categories=args.categories, emojies=args.emojies)
                        else:
                            if action == "tokenizer": line = subprocesses.tokenizer_paulo(line)
                            elif action == "detokenizer": line = subprocesses.detokenizer_paulo(line)
                            elif action == "encoder": line = encoding_fixer(text=line, filtered_categories=args.categories, emojies=args.emojies)
                        if not line.endswith('\n'):
                            line = line.rstrip() + '\n'
                        prd.write(line)

# --- Main Entry Point ---

def run() -> None:
    # Map actions to their handler functions
    handlers: Dict[str, Any] = {
        'formatter': handle_formatter,
        'recoglang': handle_recoglang,
        'fix_newlines': handle_fix_newlines,
        'jaccard': handle_jaccard,
        'deduplication': handle_deduplication,
        'pipeline': handle_pipeline_task,
        'mt_deduplication': handle_mt_deduplication,
        'mt_alignment': handle_mt_alignment,
        'normalize': handle_normalizer,
        'mt_quelingua': handle_mt_quelingua,
        'mt_transliteration': handle_mt_transliteration,
    }
    try:
        parser = build_parser(handlers)
        args = parser.parse_args()

        if not args.action:
            parser.print_help()
            return

        if os.path.exists(f"{file_dir}/temp"): shutil.rmtree(f"{file_dir}/temp")
        if args.eol:
            if hasattr(args, "path") and getattr(args, "path", None):
                args.path = convert_to_lf(args.path)
            if hasattr(args, "source") and getattr(args, "source", None):
                args.source = convert_to_lf(args.source)
            if hasattr(args, "target") and getattr(args, "target", None):
                args.target = convert_to_lf(args.target)

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