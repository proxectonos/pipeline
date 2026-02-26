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

def read_file(path: str = os.path.join(script_dir, "data/format_bel.xlsx")) -> dict:
    xls = pd.ExcelFile(path, engine='openpyxl')
    sheets = {sheet_name: pd.read_excel(xls, sheet_name) for sheet_name in xls.sheet_names}
    return sheets

def extract_rules(sheets: str, bel:bool=False) -> dict:
    logging.info(f"extracting normalization rules from file {sheets}")
    sheets = read_file(sheets)
    error_patterns = {}
    error_patterns["error"] = set(compile_patterns(sheets["error"]))
    error_patterns["RAG_fc"] = set(compile_patterns(sheets["RAG_fc"]))
    error_patterns["all"] = set(compile_patterns(sheets["all"]))
    #remove potential duplicates
    error_patterns["exact"] = set(compile_patterns(sheets["exact"]))
    if bel:
        error_patterns["transform"] = sheets["transform"]
        
    return error_patterns

def compile_patterns(df: pd.DataFrame) -> list:
    patterns = []
    logging.info(f"Compiling patterns from DataFrame with {len(df)} rows")
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
    logging.info(f"Worker initialized with detokenize={detokenize} and jsonl_field={jsonl_field}")
    _error_patterns = error_patterns
    _exact_patterns = exact_patterns
    _transform_df = transform_df
    _detokenize = detokenize
    _jsonl_field = jsonl_field

def _process_line_worker(line: str, error_patterns, exact_patterns, transform_df, detokenize, jsonl_field) -> str:
    try:
        if not jsonl_field:
            if detokenize:
                line = _detokenizer(line)
            txt_words = parse_replace(error_patterns, text=line)
            txt_words = parse_replace(exact_patterns, text=txt_words)
            return replace_patterns(transform_df, text=txt_words)
        else:
            data = json.loads(line)
            content = data.get(jsonl_field, "")
            if detokenize:
                content = _detokenizer(content)
            txt_words = parse_replace(error_patterns, text=content)
            txt_words = parse_replace(exact_patterns, text=txt_words)
            data[jsonl_field] = replace_patterns(transform_df, text=txt_words)
            return json.dumps(data, ensure_ascii=False)
    except Exception:
        sys.stderr.write(f"WORKER ERROR \n{traceback.format_exc()}\n")
        return None

def process_file(input_file: str, sheets: dict, output: str, mode: str,bel:bool=False, exact:bool=False, detokenize: bool = False, jsonl_field:str=None):
    logging.info(f"Starting normalization of file {input_file}")

    if mode == "jsonl" and jsonl_field is None:
        raise ValueError("jsonl_field must be provided when mode is 'jsonl'")
    if mode != "jsonl":
        jsonl_field = None
        
    error_patterns = sheets["error"]
    error_patterns.update(sheets["RAG_fc"])
    #error_patterns.update(sheets["all"])
    if exact:
        exact_patterns = sheets["exact"]
    if bel and "transform" in sheets:
        transform_df = sheets["transform"]
    else:
        transform_df = pd.DataFrame(columns=["pattern", "replacement"])

    total_lines = sum(1 for _ in open(input_file, "r", encoding="utf-8"))
    
    #lines = open(input_file, "r", encoding="utf-8")
      # Use a generator to avoid loading file into memory
    def stream_lines(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                yield line.strip()

    # Count lines for the progress bar without loading them all
    total_lines = sum(1 for _ in open(input_file, "r", encoding="utf-8"))

    n_jobs = max(cpu_count() - 2, 1)


    with open(output, "w", encoding="utf-8") as out:

        results = Parallel(n_jobs=n_jobs, backend="multiprocessing", batch_size=50)(
            delayed(_process_line_worker)(
                line, error_patterns, exact_patterns, transform_df, detokenize, jsonl_field
            ) for line in stream_lines(input_file)
        )

        for res in results:
            if res and res.strip(): 
                out.write(res.strip()+"\n")

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