import subprocess
import regex as re
import os
import logging
from .subprocesses import transliterate_port2gal, transliterate_port2gal_batch
import json
import sys 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


UNKNOWN_TAG = "[[UNK]]"
GEN_ERROR_TAG = "[[GEN_ERR]]"
NO_TRANS = "[[NO_TRANS]]"
cached_errors = {}
hex_pattern = r"[\x01\x02\x03]"

def replacer(match):
    tag = match.group(1)
    word = match.group(2)
    
    if word not in cached_errors:
        cached_errors[word] = transliterate_port2gal(word)
    return cached_errors[word]


def _catch_apertium_marks(input_path: str, output_path: str):
    """Process file line-by-line for optimal performance."""
    logging.info(f"Processing file for Apertium marks: {input_path}")
    
    # Combine all error patterns into single regex
    pattern = re.compile(r'\[\[(UNK|GEN_ERR|NO_TRANS)\]\]\s*(\p{L}+)')
    
    # Pass 1: Find missing words line by line
    words_to_translit = set()
    with open(input_path, "r", encoding="utf-8") as fin:
        for line in fin:
            for m in pattern.finditer(line):
                if m.group(2) not in cached_errors:
                    words_to_translit.add(m.group(2))
                    
    words_to_translit = list(words_to_translit)
    if words_to_translit:
        try:
            logging.info(f"Batch transliterating {len(words_to_translit)} words...")
            transliterated = transliterate_port2gal_batch(words_to_translit)
            print(transliterated)
            if len(transliterated) == len(words_to_translit):
                for w, tw in zip(words_to_translit, transliterated):
                    cached_errors[w] = tw
            else:
                logging.warning(f"Batch size mismatch: expected {len(words_to_translit)}, got {len(transliterated)}. Falling back to element-wise.")
        except Exception as e:
            logging.warning(f"Batch transliteration failed: {e}. Falling back to element-wise.")
            
    # Pass 2: Replace and write line by line
    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
            res = fin.read()
            res = pattern.sub(replacer, res)
            res = res.replace("[[NO_TRANS]]", "")
            res = res.replace("[[UNK]]", "")
            res = res.replace("[[GEN_ERR]]", "")
            res = res.replace("'@", "'")
            res = res.replace('-@', '-')
            res = res.replace('"@', '"')
            res = res.replace(r"\@", r"\\")
            res = res.replace("http://@www", "http://www") 
            res = re.sub(r' +([,\.!\?;:\)\]\}])', r'\1', res)  # remove space before punctuation
            res = re.sub(r' {2,}', ' ', res)  # collapse multiple spaces
            res = re.sub(hex_pattern, "", res) 
            fout.write(res)
            
    logging.debug(f"Apertium marks post-processing complete for {input_path}, saved to {output_path}")

def _make_temp_file_path(original_path: str) -> str:

    temp_input = f"temp_apertium_input_{os.getpid()}_{id(original_path)}.txt"
    with open(input_file_path, "r", encoding="utf-8") as fin, open(temp_input, "w", encoding="utf-8") as temp:
        for line in fin:
            try:
                data = json.loads(line)
                temp.write(str(data.get(field, "")) + "\n")
            except json.JSONDecodeError:
                continue # Skip malformed lines
    input_file_path = temp_input

def _write_temp_to_jsonl(output_path: str, input_file_path:str, temp_path: str, field: str):
    with open(output_path, "w+", encoding="utf-8") as fout, open(temp_path, "r", encoding="utf-8") as temp, open(input_file_path, "r", encoding="utf-8") as fin:
        for orig_line, temp_line in zip(fin, temp):
            try:
                data = json.loads(orig_line)
                data[field] = temp_line.strip()
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")
            except json.JSONDecodeError:
                raise ValueError(f"Malformed JSON line: {orig_line.strip()}")

                
def apertium_pt_gl(input_file_path: str, output_file_path: str, post_transliteration: bool = True, file_type: str = "txt", field: str = None):
    '''
    method to localise Portuguese text to the Galician standard combining symbolic translation from Apertium
    and transliteration for words not covered by the bilingual dictionary of Apertium.
    '''
    logging.info(f"Starting translation from {input_file_path} to {output_file_path}")
    if file_type == 'jsonl' and field is None:
        raise ValueError("field parameter is required when file_type is 'jsonl'")
    elif file_type == 'jsonl':
        input_file_path = _make_temp_file_path(input_file_path)

    temp_path = output_file_path + ".tmp"
    with open(input_file_path, "rb") as fin, open(temp_path, "wb") as fout:
        subprocess.run(
            [
                "docker", "run", "-i", "--rm",
                "proxectonos/apertium:3.9.12_custom_marks",
                "pt-gl"
            ],
            stdin=fin,
            stdout=fout,
            check=True
        )
    
    logging.info(f"Translation complete. Saved to {output_file_path}")
    
    if post_transliteration:
        logging.info(f"Starting post-transliteration processing for {output_file_path}")
        if file_type == 'jsonl':
            _catch_apertium_marks(temp_path, "tmp_marks.txt")
            _write_temp_to_jsonl(output_file_path, input_file_path, "tmp_marks.txt", field)
        else:
            _catch_apertium_marks(temp_path, output_file_path)
            #os.replace(temp_path, output_file_path)
    else:
        os.replace(temp_path, output_file_path)

    # Clean up temporary files
    for temp_file in [temp_path, "tmp_marks.txt"]:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    logging.info(f"Apertium translation completed: {output_file_path}")

if __name__ == "__main__":
    apertium_pt_gl("dgt.ptest", "dgt.gl")