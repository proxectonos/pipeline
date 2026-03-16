import os
import json
import fasttext
import urllib.request
from typing import List, Tuple, Optional, Dict, Any, IO
from pathlib import Path

MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
MODEL_FILENAME = "lid.176.bin"

def load_model(model_dir: Optional[str] = None) -> fasttext.FastText:
    if model_dir is None:
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
    
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, MODEL_FILENAME)
    
    if not os.path.exists(model_path):
        urllib.request.urlretrieve(MODEL_URL, model_path)
        
    fasttext.FastText.eprint = lambda x: None
    model = fasttext.load_model(model_path)
    return model

def filter_galician(path: str, mode: str = "jsonl", threshold: float = 0.05, top_k: int = 3, text_field: str = "text", parallel_file: Optional[str] = None, output_path: Optional[str] = None, parallel_output_path: Optional[str] = None):
    try:
        model = load_model()
    except Exception as e:
        raise RuntimeError(f"Failed to load fasttext model: {e}")

    removed_data: List[Any] = []
    
    # We will buffer inputs to speed up fasttext
    BATCH_SIZE = 10000

    if output_path is None:
        p = Path(path)
        out_path = p.with_name(p.stem + "_filtered" + p.suffix)
    else:
        out_path = output_path
    
    i_par: Optional[IO[str]] = open(parallel_file, "r", encoding='utf-8') if parallel_file else None
    w_par: Optional[IO[str]] = None
    if parallel_file:
        if parallel_output_path is None:
            pp = Path(parallel_file)
            par_out = pp.with_name(pp.stem + "_filtered" + pp.suffix)
        else:
            par_out = parallel_output_path
        w_par = open(par_out, "w+", encoding='utf-8')

    with open(path, "r", encoding='utf-8') as i:
        with open(out_path, "w+", encoding='utf-8') as w:
            
            buf_lines: List[str] = []
            buf_par_lines: List[str] = []
            buf_texts_to_predict: List[str] = []
            buf_data_objs: List[Optional[Dict[str, Any]]] = [] # For jsonl mode

            def process_batch():
                if not buf_texts_to_predict:
                    return
                
                # Predict in batch
                all_labels, all_probs = model.predict(buf_texts_to_predict, k=top_k)
                
                for idx, (labels, probs) in enumerate(zip(all_labels, all_probs)):
                    gl_prob = 0.0
                    for label, prob in zip(labels, probs):
                        if label == '__label__gl':
                            gl_prob = float(prob)
                            break
                            
                    is_kept = gl_prob >= threshold

                    if mode == "jsonl":
                        data = buf_data_objs[idx]
                        if data is not None and isinstance(data, dict):
                            data["lang_fasttext_gl_prob"] = float(gl_prob)
                            data["lang_fasttext_best"] = list(labels)[0].replace("__label__", "")
                            if is_kept:
                                w.write(json.dumps(data, ensure_ascii=False) + '\n')
                                if w_par:
                                    w_par.write(buf_par_lines[idx])
                            else:
                                removed_data.append(data)
                        else:
                            removed_data.append(data) # It was invalid json earlier
                    else: # txt
                        line = buf_lines[idx]
                        if is_kept:
                            w.write(line)
                            if w_par:
                                w_par.write(buf_par_lines[idx])
                        else:
                            removed_data.append(line)

                # Clear buffers
                buf_lines.clear()
                buf_par_lines.clear()
                buf_texts_to_predict.clear()
                buf_data_objs.clear()

            def get_par_line() -> Optional[str]:
                if i_par is not None:
                    return i_par.readline()
                return None

            for line in i:
                par_line = get_par_line()
                
                if mode == "jsonl":
                    try:
                        data = json.loads(line)
                        text_to_predict = data.get(text_field, "").strip().replace("\n", " ")
                        if not text_to_predict:
                            # Will handle empty string identically as bad prediction
                            buf_texts_to_predict.append("")
                            buf_data_objs.append(data)
                        else:
                            buf_texts_to_predict.append(text_to_predict)
                            buf_data_objs.append(data)
                    except json.JSONDecodeError:
                        buf_texts_to_predict.append("")
                        buf_data_objs.append(None)
                elif mode == "txt":
                    text_to_predict = line.strip().replace("\n", " ")
                    buf_texts_to_predict.append(text_to_predict)
                
                buf_lines.append(line)
                if par_line is not None:
                    buf_par_lines.append(par_line)
                    
                if len(buf_texts_to_predict) >= BATCH_SIZE:
                    process_batch()
                    
            # Process remaining
            if buf_texts_to_predict:
                process_batch()

            if removed_data:
                with open(f"{path}_removed", "w+", encoding='utf-8') as r:
                    if mode == "jsonl":
                        r.write('\n'.join([json.dumps(d, ensure_ascii=False) for d in removed_data if d is not None]) + '\n')
                    else:
                        # Removed data has \n from earlier for txt
                        r.write(''.join([d for d in removed_data]))

    if i_par:
        i_par.close()
    if w_par:
        w_par.close()

    return removed_data

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Filter Galician text.")
    parser.add_argument("-p", "--path", required=True, help="Input file path")
    parser.add_argument("-m", "--mode", default="jsonl", choices=["jsonl", "txt"])
    parser.add_argument("-t", "--threshold", type=float, default=0.05, help="Confidence threshold for GL (within top K)")
    parser.add_argument("-k", "--top_k", type=int, default=3, help="Top K predictions to consider")
    parser.add_argument("--field", default="text", help="JSONL text field")
    args = parser.parse_args()
    
    removed = filter_galician(args.path, mode=args.mode, threshold=args.threshold, top_k=args.top_k, text_field=args.field)
    print(f"Finished processing. Removed {len(removed)} items.")
