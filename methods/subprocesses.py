from collections import Counter
import subprocess
import json
import sys
import os
from pyplexity import PerplexityModel, PerplexityProcessor
from pyplexity.tag_remover import HTMLTagRemover


dir_path = os.path.dirname(os.path.realpath(__file__))


def pyplexity(path: str, args:list):

    if not args.score and not args.html_cleaning and not args.text_cleaning:
        raise Exception("No action specified for pyplexity: score, html or text")

    model = PerplexityModel.from_str(args.path_model)
    text_processor = PerplexityProcessor(perpl_model=model, perpl_limit=args.perpl_limit)
    removed_data = []

    with open(f"{path}", "r", encoding='utf-8') as i:
        with open(f"{path}_p", "w+", encoding='utf-8') as w:
            for line in i:
                #por defeito, computamos pyplexity para cada documento aka "text" field de cada linha 
                data = json.loads(line, strict=False)
                data["text"] = data["text"].strip()
                if args.score:
                    pyplexity_score = 200
                    data["pyplexity_score"] = model.compute_sentence(data["text"])
                # if args.html_cleaning:
                #     #input_string = HTMLTagRemover().process(data["text"])
                #     pass
                # if args.text_cleaning:
                #     #clean = text_processor.process(data["text"])
                #     #data["clean_text"] =  clean
                #     pass
                if args.remove_low_scores:
                    #print(data["pyplexity_score"] < args.perpl_limit, data["pyplexity_score"] )
                    if "pyplexity_score" in data and (data["pyplexity_score"] < args.perpl_limit):
                        w.write(json.dumps(data, ensure_ascii=False)+'\n')
                    else:
                        removed_data.append(data)
                else:
                    w.write(json.dumps(data, ensure_ascii=False)+'\n')

        if args.remove_low_scores and removed_data:
            with open(f"{path}_removed", "w+", encoding='utf-8') as r:
                r.write('\n'.join([json.dumps(line, ensure_ascii=False) for line in removed_data])+'\n')
    return removed_data

def quelingua_lines(path:str, args:object):
    with open(f"{path}", "r", encoding='utf-8') as i:
        with open(f"{path}_p", "w+", encoding='utf-8') as w:
            if args.mode == "jsonl":
                modified = []
                for line in i:
                    data = json.loads(line)
                    input_string = data["text"]
                    result = subprocess.run(
                    ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
                    input=input_string,
                    text=True,
                    capture_output=True,
                    )
                    #TODO: use quelingua instead of quelingua_lines to add language codes to the jsonl correctly?
                    sentences = []
                    for line in result.stdout.strip().split('\n'):
                        text, lang = line.split('\t')
                        #if args.filter_results_by_lang we create a data["text"] with the filtered lines 
                        if (args.filter_results_by_lang and lang.strip().lower() == args.filter_results_by_lang.lower()) or not args.filter_results_by_lang:
                            sentences.append([text, lang])
                    # append all sentences respecting the newlines of original file. Extract the language codes from the sentences and average most common one
                    if sentences:
                        lang_codes = [s[1] for s in sentences]
                        most_common_lang = Counter(lang_codes).most_common(1)[0][0]
                        data["text"] = "\n".join([s[0] for s in sentences])
                        data["lang"] = most_common_lang
                        if data["text"]: #avoid empty lines in jsonl after filtering LINES by language
                            w.write(json.dumps(data, ensure_ascii=False)+'\n')

            elif args.model == "txt":
                result = subprocess.run(
                        ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
                        stdin=i,
                        stdout=w,
                    )
                if args.filter_results_by_lang:
                    with open(f'{path}_p', 'r', encoding='utf-8') as p:
                        filtered_lines = []
                        for l in p.readlines():
                            sent = ''.join(l.split('\t')[:-1])
                            tag = l.split('\t')[-1]
                            if tag.strip().lower() == args.filter_results_by_lang.lower():
                                filtered_lines.append(f'{sent}\n')
                    with open(f'{path}_p', 'w+', encoding='utf-8') as p:
                        p.writelines(filtered_lines)
    return result
    '''
        with open(f"{path}", "r", encoding='utf-8') as i:
            with open(f"{path}_p", "w+", encoding='utf-8') as w:
                result = subprocess.run(
                        ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
                        stdin=i,
                        stdout=w,
                    )
    '''

def call_quelingua(input_string:str, mode:str):
    result = subprocess.run(
        ["bash", f"{dir_path}/external/quelingua_pipeline-main/quelingua_lines"],
        input=input_string,
        text=True,
        capture_output=True,
    )

    # Capture the stdout
    stdout = result.stdout
    return stdout
    '''
def quelingua(text: str, _type: str = "lines"):
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
'''

def tokenizer_paulo(text: str):
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
        raise Exception(
            f"unexpected return code {result.returncode} from subprocess {result} \nerror {result.stderr}"
        )

def detokenizer_paulo(text: str):
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


if __name__ == "__main__":
    print(quelingua(text="nada pois nada fillo nada."))
    print(detokenizer_paulo(text="nada pois nada fillo nada."))
