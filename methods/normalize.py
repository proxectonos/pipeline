from asyncio import subprocess
import logging
import pandas as pd
import re
import tqdm
import sys
import os
from multiprocessing import Pool, cpu_count
from pathlib import Path
import json
import traceback  
from joblib import Parallel, delayed
import copy
# Set up logging
#logging.basicConfig(level=logging.DEBUG, filename='normalization.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



def reinflect_verbs():
    return

script_dir = os.path.dirname(os.path.abspath(__file__))

def _detokenizer(text: str) -> str:
    result = subprocess.run(
        [
            "perl",
            f"{script_dir}/detokenizer.perl",
        ],
        input=text,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()

def _detokenizer_batch(lines: list[str]) -> list[str]:
    if not lines:
        return []
    input_str = "\n".join(lines) + "\n"
    result = subprocess.run(
        [
            "perl",
            f"{script_dir}/detokenizer.perl",
        ],
        input=input_str,
        text=True,
        capture_output=True,
        check=True,
    )
    output_str = result.stdout.strip()
    if not output_str:
        return []
    return output_str.split("\n")

def read_file(path: str = os.path.join(script_dir, "data/format_bel.xlsx")) -> dict:
    xls = pd.ExcelFile(path, engine='openpyxl')
    sheets = {sheet_name: pd.read_excel(xls, sheet_name) for sheet_name in xls.sheet_names}
    return sheets

def extract_rules(sheets_path: str, exact: bool = False, bel: bool = False) -> dict:
    """Read normalization rules from an Excel file and compile them.

    Returns a dict with keys: 'error', 'RAG_fc', 'all', 'exact', 'transform'.
    - The first four keys contain sets of compiled (pattern, replacement) tuples.
    - 'transform' is always returned as a pandas DataFrame (possibly empty)
      so callers can safely call DataFrame methods like `iterrows()`.
    """
    logging.info(f"extracting normalization rules from file {sheets_path}")
    sheets = read_file(sheets_path)
    error_patterns = {}
    logging.info(f"Compiling patterns from DataFrame 'error'")
    error_patterns["error"] = set(compile_patterns(sheets.get("error", pd.DataFrame())))
    logging.info(f"Compiling patterns from DataFrame  'RAG_fc'")
    error_patterns["RAG_fc"] = set(compile_patterns(sheets.get("RAG_fc", pd.DataFrame())))

    if exact and "exact" in sheets:
        logging.info("Compiling 'exact' patterns...")
        error_patterns["exact"] = set(compile_patterns(sheets["exact"]))
    else:
        error_patterns["exact"] = set()

    # Always provide a DataFrame for 'transform' to keep types consistent.
    if not bel:
        # If BEL-specific transforms are not requested, return an empty DataFrame
        # with the same columns (if available) so downstream code can iterate.
        logging.info("BEL-specific transforms not requested, returning empty DataFrame for 'transform'. 'All' DataFrame not loaded.")
        transform_df =  pd.DataFrame()
    else:
        logging.info(f"Compiling patterns from DataFrames 'transform' and 'all'")
        transform_df = sheets.get("transform", pd.DataFrame())
        error_patterns["all"] = set(compile_patterns(sheets.get("all", pd.DataFrame())))

    error_patterns["transform"] = transform_df
    return error_patterns

def compile_patterns(df: pd.DataFrame) -> list:
    patterns = []
    logging.info(f"Compiling {len(df)} rows")
    for index, row in df.iterrows():
        logging.debug(f"Compiling pattern from row {index}: {row[df.columns[0]]} -> {row[df.columns[1]]}")
        row[df.columns[0]] = row[df.columns[0]].strip()
        first_letter = row[df.columns[0]][0]
        erro = re.compile(r'\b' + f'[{first_letter.upper()}{first_letter.lower()}]' + re.escape(row[df.columns[0]][1:]) + r'\b')
        correct = row[df.columns[1]].strip() if isinstance(row[df.columns[1]], str) else ""
        patterns.append((erro, correct))
    return patterns

def parse_replace(patterns: list, text: str) -> str:
    for erro, correct in patterns:
        search = erro.search(text)
        if search:
            if search.span()[0] == 0 and search.group()[0].isupper():
                correct = correct.capitalize()
            logging.debug(f"erro: {erro}, {erro.pattern}: {erro.pattern}, correct: {correct}, text: {text}")
            text = erro.sub(correct, text)
    return text

def replace_patterns(df: pd.DataFrame, text: str) -> str:
    for index, row in df.iterrows():
        pattern = re.compile(row[df.columns[0]])
        replacement = row[df.columns[1]]
        if pattern.search(text):
            text = pattern.sub(replacement, text)
            logging.debug(f"pattern: {pattern.pattern}, replacement: {replacement}, text: {text}")
    return text.strip()

_error_patterns: list[tuple[re.Pattern, str]] = []
_exact_patterns: set[tuple[re.Pattern, str]] = set()
_transform_df: pd.DataFrame | None = None


def _init_worker(error_patterns, exact_patterns, transform_df, detokenize, jsonl_field):
    global _error_patterns, _exact_patterns, _transform_df, _detokenize, _jsonl_field
    _error_patterns = error_patterns
    _exact_patterns = exact_patterns
    _transform_df = transform_df
    _detokenize = detokenize
    _jsonl_field = jsonl_field

def _chunk_worker(chunk: list[str]) -> list[str]:
    results = []
    try:
        # Batch detokenize if requested and not JSON mode
        if not _jsonl_field and _detokenize:
            chunk = _detokenizer_batch(chunk)
            
        for line in chunk:
            try:
                if not _jsonl_field:
                    txt_words = parse_replace(_error_patterns, text=line)
                    txt_words = parse_replace(_exact_patterns, text=txt_words)
                    res = replace_patterns(_transform_df, text=txt_words)
                    results.append(res)
                else:
                    data = json.loads(line)
                    content = data.get(_jsonl_field, "")
                    if _detokenize:
                        content = _detokenizer(content) # Fallback to single text detokenization for JSON fields
                    txt_words = parse_replace(_error_patterns, text=content)
                    txt_words = parse_replace(_exact_patterns, text=txt_words)
                    data[_jsonl_field] = replace_patterns(_transform_df, text=txt_words)
                    results.append(json.dumps(data, ensure_ascii=False))
            except Exception:
                sys.stderr.write(f"WORKER ERROR ON LINE: {line}\n{traceback.format_exc()}\n")
                results.append(None)
    except Exception:
        sys.stderr.write(f"WORKER ERROR ON CHUNK \n{traceback.format_exc()}\n")
        # Return Nones to signify failure across the chunk but preserve output length
        results.extend([None for _ in chunk])
        
    return results

def process_file(input_file: str, sheets: dict, output: str, mode: str, detokenize: bool = False, jsonl_field:str=None):
    logging.info(f"Starting normalization of file {input_file}")

    if mode == "jsonl" and jsonl_field is None:
        raise ValueError("jsonl_field must be provided when mode is 'jsonl'")
    if mode != "jsonl":
        jsonl_field = None
        
    error_patterns = sheets["error"]
    error_patterns.update(sheets["RAG_fc"])
    #error_patterns.update(sheets["all"])
    exact_patterns = sheets["exact"]
    transform_df = sheets["transform"]

    def chunk_generator(iterable, chunk_size):
        chunk = []
        for item in iterable:
            chunk.append(item)
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def stream_lines(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                yield line.strip()

    # Count lines for the progress bar without loading them all
    total_lines = sum(1 for _ in open(input_file, "r", encoding="utf-8"))

    n_jobs = max(cpu_count() - 2, 1)

    with open(output, "w", encoding="utf-8") as out:
        chunk_size = 500
        total_chunks = (total_lines + chunk_size - 1) // chunk_size

        with Pool(processes=n_jobs, initializer=_init_worker, initargs=(error_patterns, exact_patterns, transform_df, detokenize, jsonl_field)) as pool:
            results = pool.imap(_chunk_worker, chunk_generator(stream_lines(input_file), chunk_size))
            
            for chunk_res in tqdm.tqdm(results, total=total_chunks, desc=f"Normalizing chunks"):
                for res in chunk_res:
                    if res is not None: 
                        out.write(res.strip()+"\n")
                    else:
                        out.write("\n")
                        
def process(txt: str, path_regras: str = os.path.join(script_dir, "data/format_bel.xlsx"), detokenize: bool = True):
    #process one line
    sheets = read_file(path_regras)

    logging.debug(f"sheets: {sheets.keys()}")
    error_patterns = compile_patterns(sheets["error"])
    error_patterns.update(compile_patterns(sheets["RAG_fc"]))
    error_patterns.update(compile_patterns(sheets["all"]))
    #remove potential duplicates
    logging.debug(f"Initial error patterns: {len(error_patterns)}")
    error_patterns = set(error_patterns)
    logging.debug(f"Total error patterns: {len(error_patterns)}")
    exact_patterns = set(compile_patterns(sheets["exact"]))
    logging.debug(f"Exact patterns: {len(exact_patterns)}")
    transform_df = sheets["transform"]

    if detokenize:
        args = [_detokenizer(txt), error_patterns, exact_patterns, transform_df]
    else:
        args = [txt, error_patterns, exact_patterns, transform_df]
    
    return process_line(args) 

def list_text_files(root: Path, match:str) -> list[Path]:
    return [path for path in root.rglob(match) if path.is_file()]


if __name__ == "__main__":
    '''    if len(sys.argv) > 1:
            txt_path = sys.argv[1]
        else:
            print("Please provide the path to the txt file as an argument.")
            sys.exit(1)

        process(txt_path, sheets)
    '''
    sheets = read_file()
    root = Path("/home/cesgaxuser/quelingua_corpora/corpora/es_gz/")
    for path in list_text_files(root, "*gldeduped.txt"):
        print( f"Processing file: {path}")
        process_file(str(path), sheets, detokenize=False)