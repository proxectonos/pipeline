#!/bin/bash
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

target_dir="$SCRIPT_DIR/methods/external"
mkdir -p "$target_dir"

# --- Help / Usage ---
usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [arguments...]

Nós NLP Pipeline — text cleaning toolkit for Galician corpora.

PIPELINE MODES:
  standard_pipeline <input.jsonl|input.txt>
      Monolingual cleaning pipeline for .jsonl or .txt files.
      Steps: encoder → deduplication → pyplexity → filter_lang → normalize
      Example:
        ./entrypoint.sh standard_pipeline corpus.jsonl

  mt_pipeline <source_file> <target_file> <format> [field]
      Parallel-corpus cleaning for GL-X language pairs.
      Steps: encoder → mt_deduplication → fasttext filtering → pyplexity (parallel) → mt_alignment → normalize
      Formats: txt | jsonl  (field is required for jsonl)
      Example (txt):
        ./entrypoint.sh mt_pipeline source_gl.txt target_es.txt txt
      Example (jsonl):
        ./entrypoint.sh mt_pipeline source_gl.jsonl target_es.jsonl jsonl text

  PT_GL_parallel <source_pt_file> <target_file> <format> [field]
      Portuguese-to-Galician transliteration pipeline for parallel corpora.
      Steps: encoder → mt_deduplication → Apertium transliteration → normalize
      Requires Docker (Apertium container).
      Formats: txt | jsonl  (field is required for jsonl)
      Example (txt):
        ./entrypoint.sh PT_GL_parallel source_pt.txt target_es.txt txt
      Example (jsonl):
        ./entrypoint.sh PT_GL_parallel source_pt.jsonl target_es.jsonl jsonl text

SETUP:
  install
      Clone external dependencies (port2gal, pyplexity, QueLingua) and
      install Python requirements.

INDIVIDUAL TOOLS (passed directly to main.py):
  encoder -p <path> -o <output> [-m txt|jsonl]
      Fix encoding issues in text files.

  deduplication -p <path> -o <output> [--type simple|jaccard] [-f field]
      Remove duplicate lines (simple hash or Jaccard similarity).

  mt_deduplication -s <source> -t <target> [-m txt|jsonl] [-f field]
      Deduplicate parallel files, keeping source↔target alignment.

    mt_alignment -s <source> -t <target> [-m txt|jsonl] [-f field]
      Heuristic parallel-alignment check. Writes aligned pairs, mismatched pairs,
      and a JSONL report with scores and reasons for suspicion.

  normalize -p <path> -o <output> [-m txt|jsonl] [--jsonl_field field] [--no-detokenize]
      Apply Galician normalization rules.

  pyplexity -p <path> -o <output> [--remove_low_scores] [--field field]
      Filter lines by perplexity score using a Galician bigram model.

  filter_lang -p <path> -o <output> [--filter_results_by_lang gl]
      Language identification and filtering via QueLingua.

  fasttext_gl -p <path> -o <output> [-t threshold] [-k top_k] [-f field]
      Galician language filtering via FastText.

  mt_quelingua -s <source> -t <target> -cl <lang> [-fm quelingua|fasttext]
      Language filtering for parallel corpora.

  mt_transliteration --path <path> -o <output> [-q] [-m txt|jsonl] [-f field]
      Portuguese→Galician transliteration via Apertium + port2gal.

  formatter -p <path> -o <output> [-d delimiter]
      Convert raw .txt to .jsonl using a regex delimiter.

  tokenizer -p <path> -o <output>
      Tokenize text (Galician/Latin script).

  detokenizer -p <path> -o <output>
      Reverse tokenization.

  recoglang -p <path>
      Identify the language of a text file.

OPTIONS:
  --help, -h        Show this help message
  --eol             Convert line endings to Unix (LF) format
  -w, --workers N   Number of parallel workers (default: 6)

For sub-command specific options, run:
  python3 main.py <subcommand> --help

EOF
  exit 0
}

# Handle --help / -h
if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$1" = "help" ]; then
  usage
fi

if [ -z "$1" ]; then
  echo "Error: No command specified. Use --help for usage information."
  exit 1
fi

echo "$@"

if [ "$1" = "install" ]; then

  if [ -d "$target_dir/port2gal/.git" ]; then
    if [ -n "$(git -C "$target_dir/port2gal" status --porcelain)" ]; then
      echo "port2gal has local changes; skipping pull."
    else
      echo "port2gal already exists in $target_dir, pulling latest changes..."
      git -C "$target_dir/port2gal" pull --rebase
    fi
  elif [ -d "$target_dir/port2gal" ]; then
    echo "port2gal directory exists but is not a git repo; skipping clone."
  else
    echo "Cloning port2gal into $target_dir..."
    git clone https://github.com/gamallo/port2gal.git "$target_dir/port2gal"
  fi

  if [ -d "$target_dir/pyplexity/.git" ]; then
    if [ -n "$(git -C "$target_dir/pyplexity" status --porcelain)" ]; then
      echo "pyplexity has local changes; skipping pull."
    else
      echo "pyplexity already exists in $target_dir, pulling latest changes..."
      git -C "$target_dir/pyplexity" pull --rebase
    fi
  elif [ -d "$target_dir/pyplexity" ]; then
    echo "pyplexity directory exists but is not a git repo; skipping clone."
  else
    echo "Cloning pyplexity into $target_dir..."
    git clone https://github.com/citiususc/pyplexity.git "$target_dir/pyplexity"
  fi

  if [ -d "$target_dir/quelingua_pipeline-main/.git" ]; then
    if [ -n "$(git -C "$target_dir/quelingua_pipeline-main" status --porcelain)" ]; then
      echo "QueLingua has local changes; skipping pull."
    else
      echo "QueLingua already exists in $target_dir, pulling latest changes..."
      git -C "$target_dir/quelingua_pipeline-main" pull --rebase
    fi
  elif [ -d "$target_dir/quelingua_pipeline-main" ]; then
    echo "quelingua_pipeline-main directory exists but is not a git repo; skipping clone."
  else
    echo "Cloning QueLingua into $target_dir as quelingua_pipeline-main..."
    git clone https://github.com/gamallo/QueLingua "$target_dir/quelingua_pipeline-main"
  fi
  python3 -m pip install --upgrade pip setuptools wheel
  python3 -m pip install -r requirements.txt
  echo "requirements installed. Exiting."
  exit 0

fi

if [ "$1" = "standard_pipeline" ] 
then
  if [ "$2" = "--help" ] || [ "$2" = "-h" ] || [ -z "$2" ]; then
    echo "Usage: $0 standard_pipeline <input.jsonl|input.txt>"
    echo "Monolingual pipeline: encoder -> deduplication -> pyplexity -> filter_lang -> normalize"
    exit 0
  fi

  if [[ "$2" == *.jsonl ]]; then
    extension=".jsonl"
    format="jsonl"
  elif [[ "$2" == *.txt ]]; then
    extension=".txt"
    format="txt"
  else
    echo "Error: Unsupported file format for standard_pipeline. Only .jsonl and .txt are supported."
    exit 1
  fi

  filepath=$(dirname "$2")
  filename=$(basename "$2" "$extension")
  fullpath_without_ext="$filepath/$filename"
  echo "Starting standard pipeline ($format)..."
  
  echo "Running encoder..."
  python3 "$SCRIPT_DIR/main.py" encoder -p "$2" -o "${fullpath_without_ext}_${1}_encoded${extension}" -m "$format"
  
  echo "Running deduplication..."
  python3 "$SCRIPT_DIR/main.py" deduplication -p "${fullpath_without_ext}_${1}_encoded${extension}" -o "${fullpath_without_ext}_${1}_encoded_deduplicated${extension}" --save_duplicates -m "$format" -f text
  
  echo "Running pyplexity..."
  python3 "$SCRIPT_DIR/main.py" pyplexity -p "${fullpath_without_ext}_${1}_encoded_deduplicated${extension}" -o "${fullpath_without_ext}_${1}_encoded_deduplicated_pyplexity${extension}" --remove_low_scores --field text -m "$format"
  
  echo "Running filter_lang..."
  python3 "$SCRIPT_DIR/main.py" filter_lang --filter_results_by_lang gl -p "${fullpath_without_ext}_${1}_encoded_deduplicated_pyplexity${extension}" -o "${fullpath_without_ext}_${1}_encoded_deduplicated_pyplexity_fasttext${extension}" -m "$format"
  
  echo "Running normalization..."
  if [ "$format" = "jsonl" ]; then
    python3 "$SCRIPT_DIR/main.py" normalize --mode jsonl --path "${fullpath_without_ext}_${1}_encoded_deduplicated_pyplexity_fasttext${extension}" -o "${fullpath_without_ext}_${1}_encoded_deduplicated_pyplexity_fasttext_normalized.txt" --no-detokenize --jsonl_field text
  else
    python3 "$SCRIPT_DIR/main.py" normalize --mode txt --path "${fullpath_without_ext}_${1}_encoded_deduplicated_pyplexity_fasttext${extension}" -o "${fullpath_without_ext}_${1}_encoded_deduplicated_pyplexity_fasttext_normalized.txt" --no-detokenize
  fi
 
elif [ "$1" = "PT_GL_parallel" ]
then
    if [ "$2" = "--help" ] || [ "$2" = "-h" ] || [ -z "$2" ]; then
      echo "Usage: $0 PT_GL_parallel <source_pt> <target> <format> [field]"
      echo "Format must be 'jsonl' or 'txt'. Field is required for jsonl."
      exit 0
    fi

    if [ -z "$4" ]; then
      echo "Error: Format parameter is required. Only 'jsonl' and 'txt' are supported."
      echo "Usage: $0 PT_GL_parallel <source_pt> <target> <format> [field]"
      exit 1
    fi
    
    if [ "$4" = "jsonl" ]; then
      extension=".jsonl"
    elif [ "$4" = "txt" ]; then
      extension=".txt"
    else
      echo "Error: Unsupported file extension '$4'. Only 'jsonl' and 'txt' are supported."
      exit 1
    fi

    sourcepath=$(dirname "$2")
    sourcename=$(basename "$2" "$extension")
    source_without_ext="$sourcepath/$sourcename"

    targetpath=$(dirname "$3")
    targetname=$(basename "$3" "$extension")
    target_without_ext="$targetpath/$targetname"

    if [ "$4" = "jsonl" ] && [ -z "$5" ]; then
      echo "Error: Field parameter is required for jsonl format."
      echo "Usage: $0 PT_GL_parallel <source_pt> <target> jsonl <field>"
      exit 1
    else
      field="$5"
    fi

    echo "extension set to $extension"
    echo "Starting MT pipeline for PT-GL parallel corpora..."
    
    echo "Running encoder on source file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$2" -o "${source_without_ext}_${1}_encoded${extension}" -m "$4" 
    echo "Running encoder on target file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$3" -o "${target_without_ext}_${1}_encoded${extension}" -m "$4"

    echo "Running parallel files deduplication..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_${1}_encoded${extension}" -t "${target_without_ext}_${1}_encoded${extension}" -m "$4" --field "$field"
    else
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_${1}_encoded${extension}" -t "${target_without_ext}_${1}_encoded${extension}" -m "$4"
    fi

    echo "Running Apertium MT transliteration and port2gal postprocessing"
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" mt_transliteration --path "${source_without_ext}_${1}_encoded_deduplicated${extension}" -o "${source_without_ext}_${1}_encoded_deduplicated_mt_transliterated${extension}" -m "$4" --field "$field" -q 
    else
      python3 "$SCRIPT_DIR/main.py" mt_transliteration --path "${source_without_ext}_${1}_encoded_deduplicated${extension}" -o "${source_without_ext}_${1}_encoded_deduplicated_mt_transliterated${extension}" -m "$4" -q
    fi

    echo "Running normalization on the new GL file..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" normalize --path "${source_without_ext}_${1}_encoded_deduplicated_mt_transliterated${extension}" -o "${source_without_ext}_${1}_encoded_deduplicated_mt_transliterated_normalized${extension}" --mode "$4" --jsonl_field "$field" --no-detokenize
    else
      python3 "$SCRIPT_DIR/main.py" normalize --path "${source_without_ext}_${1}_encoded_deduplicated_mt_transliterated${extension}" -o "${source_without_ext}_${1}_encoded_deduplicated_mt_transliterated_normalized${extension}" --mode "$4" --no-detokenize
    fi
    
    echo "Renaming final output files..."
    mv "${source_without_ext}_${1}_encoded_deduplicated_mt_transliterated_normalized${extension}" "${source_without_ext}_${1}_final${extension}"
    mv "${target_without_ext}_${1}_encoded_deduplicated${extension}" "${target_without_ext}_${1}_final${extension}"
    
    echo "MT PT to GL-X_parallel pipeline finished."

elif [ "$1" = "mt_pipeline" ]
then
    if [ "$2" = "--help" ] || [ "$2" = "-h" ] || [ -z "$2" ]; then
      echo "Usage: $0 mt_pipeline <source_gl> <target> <format> [field]"
      echo "Format must be 'jsonl' or 'txt'. Field is required for jsonl."
      exit 0
    fi

    if [ -z "$4" ]; then
      echo "Error: Format parameter is required. Only 'jsonl' and 'txt' are supported."
      echo "Usage: $0 mt_pipeline <source_gl> <target> <format> [field]"
      exit 1
    fi
    
    if [ "$4" = "jsonl" ]; then
      extension=".jsonl"
    elif [ "$4" = "txt" ]; then
      extension=".txt"
    else
      echo "Error: Unsupported file extension '$4'. Only 'jsonl' and 'txt' are supported."
      exit 1
    fi

    sourcepath=$(dirname "$2")
    sourcename=$(basename "$2" "$extension")
    source_without_ext="$sourcepath/$sourcename"

    targetpath=$(dirname "$3")
    targetname=$(basename "$3" "$extension")
    target_without_ext="$targetpath/$targetname"

    if [ "$4" = "jsonl" ] && [ -z "$5" ]; then
      echo "Error: Field parameter is required for jsonl format."
      echo "Usage: $0 mt_pipeline <source_gl> <target> jsonl <field>"
      exit 1
    else
      field="$5"
    fi

    echo "extension set to $extension"
    echo "Starting MT pipeline for GL-X parallel corpora..."
    
    echo "Running encoder on source file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$2" -o "${source_without_ext}_${1}_encoded${extension}" -m "$4" 
    echo "Running encoder on target file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$3" -o "${target_without_ext}_${1}_encoded${extension}" -m "$4"

    echo "Running parallel files deduplication..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_${1}_encoded${extension}" -t "${target_without_ext}_${1}_encoded${extension}" -m "$4" --field "$field"
    else
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_${1}_encoded${extension}" -t "${target_without_ext}_${1}_encoded${extension}" -m "$4"
    fi

    echo "Running fasttext language filtering using SOURCE file..."
    if [ "$4" = "jsonl" ]; then
       python "$SCRIPT_DIR/main.py" fasttext_gl \
       --path   "${source_without_ext}_${1}_encoded_deduplicated${extension}"\
       --output "${source_without_ext}_${1}_encoded_deduplicated_fasttext${extension}" \
       --parallel_file "${target_without_ext}_${1}_encoded_deduplicated${extension}" \
       --parallel_output "${target_without_ext}_${1}_encoded_deduplicated_fasttext${extension}" \
       --mode jsonl \
       --text_field "$field" \
       --threshold 0.5
    else

      python "$SCRIPT_DIR/main.py" fasttext_gl \
       --path   "${source_without_ext}_${1}_encoded_deduplicated${extension}"\
       --output "${source_without_ext}_${1}_encoded_deduplicated_fasttext${extension}" \
       --parallel_file "${target_without_ext}_${1}_encoded_deduplicated${extension}" \
       --parallel_output "${target_without_ext}_${1}_encoded_deduplicated_fasttext${extension}" \
       --mode txt \
       --threshold 0.5
    fi

    src_fasttext="${source_without_ext}_${1}_encoded_deduplicated_fasttext${extension}"
    tgt_fasttext="${target_without_ext}_${1}_encoded_deduplicated_fasttext${extension}"
    src_pyplexity="${source_without_ext}_${1}_encoded_deduplicated_fasttext_pyplexity${extension}"
    tgt_pyplexity="${target_without_ext}_${1}_encoded_deduplicated_fasttext_pyplexity${extension}"
    src_aligned="${source_without_ext}_${1}_encoded_deduplicated_fasttext_pyplexity_alignment${extension}"
    tgt_aligned="${target_without_ext}_${1}_encoded_deduplicated_fasttext_pyplexity_alignment${extension}"

    echo "Running pyplexity filtering using SOURCE file with parallel TARGET propagation..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" pyplexity -p "$src_fasttext" -o "$src_pyplexity" -pf "$tgt_fasttext" -po "$tgt_pyplexity" --remove_low_scores --field "$field" -m "$4"
    else
      python3 "$SCRIPT_DIR/main.py" pyplexity -p "$src_fasttext" -o "$src_pyplexity" -pf "$tgt_fasttext" -po "$tgt_pyplexity" --remove_low_scores -m "$4"
    fi

    echo "Running MT alignment quality filter on SOURCE-TARGET pairs..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" mt_alignment -s "$src_pyplexity" -t "$tgt_pyplexity" -f "$field" -m "$4"
    else
      python3 "$SCRIPT_DIR/main.py" mt_alignment -s "$src_pyplexity" -t "$tgt_pyplexity" -m "$4"
    fi

    echo "Running normalization on the new GL file..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" normalize --path "$src_aligned" -o "${source_without_ext}_${1}_encoded_deduplicated_fasttext_pyplexity_alignment_normalized${extension}" -m "$4" --jsonl_field "$field" --no-detokenize
    else
      python3 "$SCRIPT_DIR/main.py" normalize --path "$src_aligned" -o "${source_without_ext}_${1}_encoded_deduplicated_fasttext_pyplexity_alignment_normalized${extension}" -m "$4" --no-detokenize
    fi
    
    echo "Renaming final output files..."
    mv "${source_without_ext}_${1}_encoded_deduplicated_fasttext_pyplexity_alignment_normalized${extension}" "${source_without_ext}_${1}_final${extension}"
    mv "$tgt_aligned" "${target_without_ext}_${1}_final${extension}"

    echo "MT GL-X parallel pipeline finished."

else
  cmd="$1"
  shift

  global_opts=()
  forwarded=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --eol|--no-eol)
        global_opts+=("$1")
        shift
        ;;
      -w|--workers)
        if [ -n "$2" ]; then
          global_opts+=("$1" "$2")
          shift 2
        else
          echo "Error: $1 requires a value."
          exit 1
        fi
        ;;
      *)
        forwarded+=("$1")
        shift
        ;;
    esac
  done

  echo "Running $SCRIPT_DIR/main.py with arguments: ${global_opts[*]} $cmd ${forwarded[*]}"
  python3 "$SCRIPT_DIR/main.py" "${global_opts[@]}" "$cmd" "${forwarded[@]}"
fi