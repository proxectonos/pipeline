import subprocess
import regex as re
import os
import logging
from .subprocesses import transliterate_port2gal
import json
import sys 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


UNKNOWN_TAG = "[[UNK]]"
GEN_ERROR_TAG = "[[GEN_ERR]]"
cached_errors = {}

def _catch_apertium_marks(input_path: str, output_path: str):
    """Process file line-by-line to handle large files efficiently."""
    unknown_marks_regex = rf"\[\[UNK\]\]\s*(\p{{L}}+)"
    gen_error_regex = rf"\[\[GEN_ERR\]\]\s*(\p{{L}}+)"
    left_ats = r'(?<=\s|^|["\'!?])@(\p{L}+)'

    logging.info(f"Processing file for Apertium marks: {input_path}")
    
    with open(input_path, "r") as fin, open(output_path, "w") as fout:
        for line_number, line in enumerate(fin, start=1):
            logging.debug(f"Processing line {line_number}: {line.strip()}")
            unknowns = re.findall(unknown_marks_regex, line)
            unknowns += re.findall(left_ats, line)
            gen_errors = re.findall(gen_error_regex, line)
            logging.debug(f"Line {line_number}: Found {len(unknowns)} unknowns and {len(gen_errors)} generation errors. {unknowns}")  
            
            for word in unknowns:
                if word not in cached_errors:
                    cached_errors[word] = transliterate_port2gal(word)
                logging.debug(f"Line {line_number}: Transliteration for '{word}' is '{cached_errors[word]}'")
                line = line.replace(f"{UNKNOWN_TAG}{word}", cached_errors[word])

            for gen_err in gen_errors:
                if gen_err not in cached_errors:
                    cached_errors[gen_err] = transliterate_port2gal(gen_err)
                line = line.replace(f"{GEN_ERROR_TAG}{gen_err}", cached_errors[gen_err])

            fout.write(line.replace("http://@www", "http://www")) # Fix for a specific edge case where Apertium might produce an incorrect URL with an extra '@' symbol.
            logging.debug(f"Processed line {line_number}: {line.strip()}")

def _make_temp_file_path(original_path: str) -> str:

    temp_input = "temp_apertium_input.txt"
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