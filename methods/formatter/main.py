import json
import argparse
import glob
import os
import re

def format_chunk(chunk:str,id:int):
    word_count = len(chunk.split())
    data ={
        "id": id,
        "text": chunk,
        "num_words": word_count
    }
    return data

def process_folder(input, output):
    files = glob.glob(input)
    return

def process_text_delimiter(input_file, delimiter, output_file):
    running_text = ""
    buffer = 4080
    text_id = 0
    result_data = []
    with open(input_file, 'r', encoding='utf-8') as file:

        while True:
            chunk = file.read(buffer)
            if not chunk:
                break
            
            chunk = running_text + chunk
            #leave the last chunk as running text since it hasn't been split yet
            #parts = chunk.split(delimiter)
            parts = re.split(delimiter, chunk)
            for _, text in enumerate(parts[:-1]):
                text = text.strip()
                #print(_, text, delimiter)
                #print(text_id, len(text.split()),text)
                result_data.append(format_chunk(text,text_id))
                text_id += 1
            running_text = parts[-1]

            if len(result_data) > 1000:
                save_to_json_lines(result_data,output_file)
                result_data = []
        if running_text:
            result_data.append(format_chunk(running_text,text_id))

        if result_data:
                save_to_json_lines(result_data,output_file)
    return result_data

def save_to_json_lines(data, output_file):
    with open(output_file, 'a+', encoding='utf-8') as file:
        for entry in data:
            print(entry)
            json_line = json.dumps(entry, ensure_ascii=False)
            file.write(json_line + '\n')

def run(input:str, method:str, output:str, delimiter:str='\n\n\n'):
    print(f"Running formatter with delimiter {delimiter}")
    if method == 'regex':
            new_file = open(output, 'w+', encoding='utf-8')
            new_file.close()
            process_text_delimiter(input, delimiter, output)
    elif method == 'folder':
            process_folder(input=input)

if __name__ == "__main__":
    run('test.txt','regex','out_test.jsonl', delimiter='\n\n\n')
