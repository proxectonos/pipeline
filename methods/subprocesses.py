from collections import Counter
import subprocess
import json
import sys
import os
import pickle
import argparse
from typing import Iterator, Any, List, Optional, Union, Generator, Dict, IO
from pyplexity import PerplexityModel, PerplexityProcessor
from pyplexity.tag_remover import HTMLTagRemover
import tqdm
import logging 
from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


dir_path = os.path.dirname(os.path.realpath(__file__))

# Module-level model cache (shared by forked workers via copy-on-write)
_pyplexity_model: Optional[PerplexityModel] = None
_pyplexity_model_path: Optional[str] = None


def load_pyplexity_model(model_path: str) -> PerplexityModel:
    """Load pyplexity model with pickle caching and singleton reuse.
    
    First call from .st: ~94s.  Subsequent calls from .pkl cache: ~17s.
    When called before fork(), child processes inherit the model via COW: 0s.
    """
    global _pyplexity_model, _pyplexity_model_path
    if _pyplexity_model is not None and _pyplexity_model_path == model_path:
        return _pyplexity_model

    pkl_path = model_path + '.pkl'
    if os.path.exists(pkl_path) and os.path.getmtime(pkl_path) >= os.path.getmtime(model_path):
        logging.info(f"Loading pyplexity model from pickle cache: {pkl_path}")
        with open(pkl_path, 'rb') as f:
            _pyplexity_model = pickle.load(f)
    else:
        logging.info(f"Loading pyplexity model from .st file: {model_path}")
        _pyplexity_model = PerplexityModel.from_str(model_path)
        try:
            with open(pkl_path, 'wb') as f:
                pickle.dump(_pyplexity_model, f, protocol=pickle.HIGHEST_PROTOCOL)
            logging.info(f"Saved pickle cache: {pkl_path}")
        except Exception as e:
            logging.warning(f"Failed to save pickle cache: {e}")

    _pyplexity_model_path = model_path
    return _pyplexity_model


def mt_assert_parallel(src_file: str, tgt_file: str) -> None:
    #check that both files have the same number of lines 
    with open(src_file, "r", encoding='utf-8') as src:
        with open(tgt_file, "r", encoding='utf-8') as tgt:
            src_lines = src.readlines()
            tgt_lines = tgt.readlines()
            if len(src_lines) != len(tgt_lines):
                raise Exception(f"Source and target files have different number of lines: {len(src_lines)} and {len(tgt_lines)}")
    return

def read_file_line_by_line(file: str) -> Generator[str, None, None]:
    with open(file, "r", encoding='utf-8') as f:
        for line in f:
            yield line


def mt_quelingua(args: argparse.Namespace) -> None:
    # Determine which filter to use
    method = getattr(args, 'filter_method', 'quelingua')
    
    if method == 'fasttext':
        from .galician_filter import filter_galician
        src_base = str(Path(args.source).with_suffix(''))
        tgt_base = str(Path(args.target).with_suffix(''))
        src_ext = Path(args.source).suffix
        tgt_ext = Path(args.target).suffix
        tag = getattr(args, 'output_tag', '_fasttext')
        filter_galician(
            path=args.source,
            mode=args.mode,
            threshold=getattr(args, 'threshold', 0.4),
            top_k=getattr(args, 'top_k', 3),
            text_field=getattr(args, 'field', 'text'),
            parallel_file=args.target,
            output_path=f"{src_base}{tag}{src_ext}",
            parallel_output_path=f"{tgt_base}{tag}{tgt_ext}",
        )
        return

    # Original Quelingua implementation
    src_file = args.source
    tgt_file = args.target
    src_base = Path(args.source).with_suffix('')
    tgt_base = Path(args.target).with_suffix('')

    correct_lang = args.correct_lang_source
    if args.mode != 'txt':
        raise Exception("Not implemented yet. Only txt files are supported for MT parallel dataset processing ")
    
    # Efficient line count for tqdm
    len_src = 0
    with open(src_file, 'rb') as f:
        for _ in f: len_src += 1
    
    logging.info(f"Processing {len_src} lines from {src_file} and {tgt_file}")
    
    with open(f'{src_base}{args.output_tag}', 'w+', encoding='utf-8') as s, open(f'{tgt_base}{args.output_tag}', 'w+', encoding='utf-8') as t, open(f'{src_base}{args.output_tag}_mismatched', 'w+', encoding='utf-8') as m_src, open(f'{tgt_base}{args.output_tag}_mismatched', 'w+', encoding='utf-8') as m_tgt:
        src_file_generator = read_file_line_by_line(src_file)
        tgt_file_generator = read_file_line_by_line(tgt_file)

        BATCH_SIZE = 10000
        src_batch: List[str] = []
        tgt_batch: List[str] = []
        
        def process_batch(sb: List[str], tb: List[str]) -> None:
            input_str = "".join(sb)
            src_result = subprocess.run(
                ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
                input=input_str,
                text=True,
                capture_output=True,
            )
            out_lines = src_result.stdout.strip('\n').split('\n')
            
            for i, (sl, tl) in enumerate(zip(sb, tb)):
                if i < len(out_lines):
                    parts = out_lines[i].split('\t')
                    src_lang_tag = parts[-1].strip() if len(parts) > 1 else ""
                else:
                    src_lang_tag = ""
                    
                if src_lang_tag.strip().lower() != correct_lang.lower():
                    m_src.write(sl)
                    m_tgt.write(tl)
                else:
                    s.write(sl)
                    t.write(tl)

        for idx, (src_line, tgt_line) in enumerate(tqdm.tqdm(zip(src_file_generator, tgt_file_generator), total=len_src)):
            src_batch.append(src_line)
            tgt_batch.append(tgt_line)
            if len(src_batch) >= BATCH_SIZE:
                process_batch(src_batch, tgt_batch)
                src_batch = []
                tgt_batch = []
                
        if src_batch:
            process_batch(src_batch, tgt_batch)
    
    logging.info(f"Finished processing. Output written to {src_base}{args.output_tag} and {tgt_base}{args.output_tag}")

def pyplexity(path: str, args: argparse.Namespace, parallel_file: Optional[str] = None) -> List[Any]:

    if not getattr(args, 'score', False) and \
       not getattr(args, 'html_cleaning', False) and \
       not getattr(args, 'text_cleaning', False):
        raise Exception("No action specified for pyplexity: score, html or text")

    model = load_pyplexity_model(args.path_model)
    text_processor = PerplexityProcessor(perpl_model=model, perpl_limit=args.perpl_limit)
    removed_data: List[Any] = []

    i_par: Optional[IO[str]] = open(parallel_file, "r", encoding='utf-8') if parallel_file else None
    w_par: Optional[IO[str]] = open(f"{parallel_file}_p", "w+", encoding='utf-8') if parallel_file else None

    with open(f"{path}", "r", encoding='utf-8') as i:
        with open(f"{path}_p", "w+", encoding='utf-8') as w:
            # Use zip to iterate over both files simultaneously, handling the case where i_par is None
            import itertools
            parallel_gen = i_par if i_par else itertools.cycle([None])
            
            for line_any, par_line_any in zip(i, parallel_gen):
                line = str(line_any)
                par_line = str(par_line_any) if par_line_any is not None else None
                
                if args.mode == "jsonl":
                    try:
                        data = json.loads(line, strict=False)
                        text = data.get("text", "").strip()
                        if not text:
                            # If text is empty, we keep it but it will have a 0 score or we skip it?
                            # Standard logic skips scoring on empty strings but keeps them if not removing
                            pyplexity_score = 0.0 
                        else:
                            pyplexity_score = model.compute_sentence(text)
                        
                        data["pyplexity_score"] = pyplexity_score
                        
                        if args.remove_low_scores:
                            if pyplexity_score < args.perpl_limit:
                                w.write(json.dumps(data, ensure_ascii=False) + '\n')
                                if w_par and par_line is not None: w_par.write(par_line)
                            else:
                                removed_data.append(data)
                        else:
                            w.write(json.dumps(data, ensure_ascii=False) + '\n')
                            if w_par and par_line is not None: w_par.write(par_line)
                    except json.JSONDecodeError:
                        # Handle bad lines gracefully
                        removed_data.append(line)
                else:
                    # process .txt files
                    stripped_line = line.strip()
                    if not stripped_line:
                        # For empty lines, what is the desired behavior?
                        # Usually we keep them or assign a neutral score.
                        # Let's say we keep them (score 0)
                        pyplexity_score = 0.0
                    else:
                        pyplexity_score = model.compute_sentence(stripped_line)
                        
                    if args.remove_low_scores:
                        if pyplexity_score < args.perpl_limit:
                            w.write(line) # Keep original line with newline
                            if w_par and par_line is not None:
                                w_par.write(par_line)
                        else:
                            removed_data.append(line)
                    else:
                        w.write(line)
                        if w_par and par_line is not None:
                            w_par.write(par_line)

    # FINAL WRITE for removed data - MOVED OUTSIDE THE LOOP
    if args.remove_low_scores and removed_data:
        with open(f"{path}_removed", "w+", encoding='utf-8') as r:
            if args.mode == "jsonl":
                # Ensure all items are serialized to JSON string
                r.write('\n'.join([json.dumps(obj, ensure_ascii=False) if isinstance(obj, dict) else str(obj) for obj in removed_data]) + '\n')
            else:
                # Ensure all items are strings
                r.write(''.join([str(l) for l in removed_data]))

    if i_par: i_par.close()
    if w_par: w_par.close()

    return removed_data

def quelingua_lines(path: str, args: argparse.Namespace, parallel_file: Optional[str] = None) -> None:
    # We buffer requests to speed up subprocess calling and avoid Out of Memory
    BATCH_SIZE = 10000

    i_par = open(parallel_file, "r", encoding='utf-8') if parallel_file else None
    w_par = open(f"{parallel_file}_p", "w+", encoding='utf-8') if parallel_file else None

    with open(f"{path}", "r", encoding='utf-8') as i:
        with open(f"{path}_p", "w+", encoding='utf-8') as w:
            
            buf_lines: List[str] = []
            buf_par_lines: List[str] = []
            buf_inputs: List[str] = []
            buf_data_objs: List[Dict[str, Any]] = [] # jsonl specific objects
            
            def process_batch() -> None:
                if not buf_inputs:
                    return
                input_string = "\n".join(buf_inputs) + "\n"
                result = subprocess.run(
                    ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
                    input=input_string,
                    text=True,
                    capture_output=True,
                )
                
                out_lines = result.stdout.strip("\n").split("\n") if result.stdout else []
                
                for idx in range(len(buf_inputs)):
                    is_kept = False # defaults to false if empty
                    tag = ""
                    
                    if idx < len(out_lines):
                        parts = out_lines[idx].split('\t')
                        if len(parts) >= 2:
                            tag = parts[1].strip()
                            if (not args.filter_results_by_lang) or (tag.lower() == args.filter_results_by_lang.lower()):
                                is_kept = True
                                
                    if mode == "jsonl":
                        data = buf_data_objs[idx]
                        if tag:
                            data["lang"] = tag
                        if is_kept:
                            w.write(json.dumps(data, ensure_ascii=False) + '\n')
                            if w_par: w_par.write(buf_par_lines[idx])
                    else: # txt
                        if is_kept:
                            w.write(f'{buf_lines[idx].strip()}\n')
                            if w_par: w_par.write(buf_par_lines[idx])
                
                buf_lines.clear()
                buf_par_lines.clear()
                buf_inputs.clear()
                buf_data_objs.clear()

            mode = args.mode
            for line in i:
                par_line = i_par.readline() if i_par else None
                
                if mode == "jsonl":
                    data = json.loads(line)
                    buf_data_objs.append(data)
                    buf_inputs.append(data["text"].replace('\n', ' '))
                elif mode == "txt":
                    buf_inputs.append(line.replace('\n', ' '))
                
                buf_lines.append(line)
                if par_line is not None:
                    buf_par_lines.append(par_line)
                    
                if len(buf_inputs) >= BATCH_SIZE:
                    process_batch()
            
            if buf_inputs:
                process_batch()

    if i_par: i_par.close()
    if w_par: w_par.close()

def call_quelingua(input_string: str, mode: str) -> str:
    result = subprocess.run(
        ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
        input=input_string,
        text=True,
        capture_output=True,
    )

    # Capture the stdout
    stdout = result.stdout
    return stdout

def quelingua(text: str, _type: str = "lines") -> Union[List[str], str]:
    if _type == "lines":
        #text input is a str line from file
        echo_sentence = subprocess.Popen(["echo", f"{text}"], stdout=subprocess.PIPE)
        result = subprocess.run(
            ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
            stdin=echo_sentence.stdout,
            stdout=subprocess.PIPE,
        )
        return [text, result.stdout.decode("utf-8").strip()]
    elif _type == "whole":
        #read whole file line by line and tag em
        cat_text = subprocess.Popen(["cat", f"{text}"], stdout=subprocess.PIPE)
        result = subprocess.run(
            ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua"],
            stdin=cat_text.stdout,
            stdout=subprocess.PIPE,
        )
        return result.stdout.decode("utf-8").strip()
    return ""

def tokenizer_paulo(text: str) -> str:
    echo_sentence = subprocess.Popen(["echo", f"{text}"], stdout=subprocess.PIPE)
    result = subprocess.run(
        [
            "perl",
            f"{dir_path}/external/tokenization/tokens-gl_exe_esp.perl",
        ],
        stdin=echo_sentence.stdout,
        stdout=subprocess.PIPE,
    )
    if result.returncode == 0:
        return result.stdout.decode("utf-8").strip()
    else:
        err_msg = result.stderr.decode('utf-8') if result.stderr else 'None'
        raise Exception(
            f"unexpected return code {result.returncode} from subprocess {result} \nerror {err_msg}"
        )

def detokenizer_paulo(text: str) -> str:
    echo_sentence = subprocess.Popen(["echo", f"{text}"], stdout=subprocess.PIPE)
    result = subprocess.run(
        [
            "perl",
            f"{dir_path}/external/tokenization/detokenizer.perl",
        ],
        stdin=echo_sentence.stdout,
        stdout=subprocess.PIPE,
    )
    if result.returncode == 0:
        return result.stdout.decode("utf-8").strip()
    else:
        raise Exception(
            f"unexpected return code {result.returncode} from subprocess {result}"
        )

def transliterate_port2gal_batch(words: List[str]) -> List[str]:
    if not words:
        return []
    input_str = "\n".join(words) + "\n"
    result = subprocess.run(
        [
            "perl",
            f"{dir_path}/external/port2gal/port2gal.perl",
        ],
        input=input_str.encode("utf-8"),
        stdout=subprocess.PIPE,
    )
    if result.returncode == 0:
        output_str = result.stdout.decode("utf-8").strip()
        if not output_str:
            return []
        return output_str.split("\n")
    else:
        raise Exception(
            f"unexpected return code {result.returncode} from batch transliteration"
        )

def transliterate_port2gal(text: str) -> str:
    echo_sentence = subprocess.Popen(["echo", f"{text}"], stdout=subprocess.PIPE)
    result = subprocess.run(
        [
            "perl",
            f"{dir_path}/external/port2gal/port2gal.perl",
        ],
        stdin=echo_sentence.stdout,
        stdout=subprocess.PIPE,
    )
    if result.returncode == 0:
        logging.debug(f"Transliterated {text} to {result.stdout.decode('utf-8').strip()}")
        return result.stdout.decode("utf-8").strip()
    else:
        raise Exception(
            f"unexpected return code {result.returncode} from subprocess {result}"
        )
if __name__ == "__main__":
    print(quelingua(text="nada pois nada fillo nada."))
    print(detokenizer_paulo(text="nada pois nada fillo nada."))
