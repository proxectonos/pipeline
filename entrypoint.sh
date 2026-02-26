#!/bin/bash
set -e
echo "$@"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

target_dir="$SCRIPT_DIR/methods/external"
mkdir -p "$target_dir"

if [ $1 = "install" ]; then
  echo "No pipeline specified. Exiting."
  exit 1
if [ -d "$target_dir/port2gal/.git" ]; then
  echo "port2gal already exists in $target_dir, pulling latest changes..."
  git -C "$target_dir/port2gal" pull --rebase
else
  echo "Cloning port2gal into $target_dir..."
  git clone https://github.com/gamallo/port2gal.git "$target_dir/port2gal"
fi

if [ -d "$target_dir/pyplexity/.git" ]; then
  echo "pyplexity already exists in $target_dir, pulling latest changes..."
  git -C "$target_dir/pyplexity" pull --rebase
else
  echo "Cloning pyplexity into $target_dir..."
  git clone https://github.com/citiususc/pyplexity.git "$target_dir/pyplexity"
fi

if [ -d "$target_dir/quelingua_pipeline-main/.git" ]; then
  echo "QueLingua already exists in $target_dir, pulling latest changes..."
  git -C "$target_dir/quelingua_pipeline-main" pull --rebase
else
  echo "Cloning QueLingua into $target_dir as quelingua_pipeline-main..."
  git clone https://github.com/gamallo/QueLingua "$target_dir/quelingua_pipeline-main"
fi
pip install -r requirements.txt
fi

if [ $1 = "standard_pipeline" ] 
then
  filepath=$(dirname "$2")
  filename=$(basename "$2" .jsonl)
  fullpath_without_ext="$filepath/$filename"
  echo "Starting standard pipeline..."
  
   echo "Running encoder..."
   python3 "$SCRIPT_DIR/main.py" encoder -p $2 -o $fullpath_without_ext"_encoded.jsonl"
  
   echo "Running deduplication..."
   python3 "$SCRIPT_DIR/main.py" deduplication -p $fullpath_without_ext"_encoded.jsonl" -o $fullpath_without_ext"_encoded_deduplicated.jsonl" --save_duplicates
  
   echo "Running pyplexity..."
   python3 "$SCRIPT_DIR/main.py" pyplexity -p $fullpath_without_ext"_encoded_deduplicated.jsonl" -o $fullpath_without_ext"_encoded_deduplicated_pyplexity.jsonl" --remove_low_scores
  
  echo "Running filter_lang..."
  python3 "$SCRIPT_DIR/main.py" filter_lang --filter_results_by_lang gl -p $fullpath_without_ext"_encoded_deduplicated_pyplexity.jsonl" -o  $fullpath_without_ext"_encoded_deduplicated_pyplexity_quelingua.jsonl"

  echo "Running normalization..."
  python3 "$SCRIPT_DIR/main.py" normalize --mode jsonl --path  $fullpath_without_ext"_encoded_deduplicated_pyplexity_quelingua.jsonl" --o  $fullpath_without_ext"_encoded_deduplicated_pyplexity_quelingua_normalized.txt" --no-detokenize
 
elif [ "$1" = "PT_GL_parallel" ]
then
    if [ -z "$4" ]; then
      echo "Error: Format parameter is required. Only 'jsonl' and 'txt' are supported."
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

    # DEFINE PATHS BEFORE USING THEM
    sourcepath=$(dirname "$2")
    sourcename=$(basename "$2" "$extension")
    source_without_ext="$sourcepath/$sourcename"

    targetpath=$(dirname "$3")
    targetname=$(basename "$3" "$extension")
    target_without_ext="$targetpath/$targetname"

    if [ "$4" = "jsonl" ] && [ -z "$5" ]; then
      echo "Error: Field parameter is required for jsonl format."
      echo "Please specify the text field inside the jsonl file (e.g., 'txt', 'content', etc.):"
      read -r field_name
      if [ -z "$field_name" ]; then
        echo "Error: No field specified. Exiting."
        exit 1
      fi
      field="$field_name"
    else
      field="$5"
    fi

    echo "extension set to $extension"
    echo "Starting MT pipeline for PT-GL parallel corpora..."
    echo "files: $2 (source), $3 (target), format: $4, field: $field"
    
    echo "Running encoder on source file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$2" -o "${source_without_ext}_encoded${extension}" -m "$4" 
    echo "Running encoder on target file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$3" -o "${target_without_ext}_encoded${extension}" -m "$4"

    echo "Running parallel files deduplication..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_encoded${extension}" -t "${target_without_ext}_encoded${extension}" -m "$4" --field "$field"
    else
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_encoded${extension}" -t "${target_without_ext}_encoded${extension}" -m "$4"
    fi

    echo "Running Apertium MT transliteration and port2gal postprocessing"
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" mt_transliteration --path "${source_without_ext}_encoded_deduplicated${extension}" -o "${source_without_ext}_encoded_deduplicated_mt_transliterated${extension}" -m "$4" --field "$field" -q 
    else
      python3 "$SCRIPT_DIR/main.py" mt_transliteration --path "${source_without_ext}_encoded_deduplicated${extension}" -o "${source_without_ext}_encoded_deduplicated_mt_transliterated${extension}" -m "$4" -q
    fi
    echo "Running normalization on the new GL file..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" normalize --path "${source_without_ext}_encoded_deduplicated_mt_transliterated${extension}" --o "${source_without_ext}_encoded_deduplicated_mt_transliterated_normalized${extension}" --mode "$4" --json_field "$field" --no-detokenize
    else
      python3 "$SCRIPT_DIR/main.py" normalize --path "${source_without_ext}_encoded_deduplicated_mt_transliterated${extension}" --o "${source_without_ext}_encoded_deduplicated_mt_transliterated_normalized${extension}" --mode "$4" --no-detokenize
    fi
    
    
    echo "Renaming final output files..."
    mv "${source_without_ext}_encoded_deduplicated_mt_transliterated_normalized${extension}" "gl_final${extension}"
    mv "${target_without_ext}_encoded_deduplicated${extension}" "${target_without_ext}_final${extension}"

    echo "Cleaning up intermediate files..."
    rm -f "${source_without_ext}_encoded${extension}"
    rm -f "${target_without_ext}_encoded${extension}"
    rm -f "${source_without_ext}_encoded_deduplicated${extension}"
    rm -f "${target_without_ext}_encoded_deduplicated${extension}"
    rm -f "${source_without_ext}_encoded_deduplicated_mt_transliterated${extension}"
  
    echo "MT  PT to GL-X_parallel pipeline finished."

elif [ "$1" = "mt_pipeline" ]
then
    echo "Running MT GL-X pipeline with arguments: $@"

    if [ -z "$4" ]; then
      echo "Error: Format parameter is required. Only 'jsonl' and 'txt' are supported."
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
      echo "Please specify the text field inside the jsonl file (e.g., 'txt', 'content', etc.):"
      read -r field_name
      if [ -z "$field_name" ]; then
        echo "Error: No field specified. Exiting."
        exit 1
      fi
      field="$field_name"
    else
      field="$5"
    fi

    echo "extension set to $extension"
    echo "Starting MT pipeline for GL-X parallel corpora..."
    echo "files: $2 (source), $3 (target), format: $4, field: $field"
    
    echo "Running encoder on source file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$2" -o "${source_without_ext}_encoded${extension}" -m "$4" 
    echo "Running encoder on target file..."
    python3 "$SCRIPT_DIR/main.py" encoder -p "$3" -o "${target_without_ext}_encoded${extension}" -m "$4"

    echo "Running parallel files deduplication..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_encoded${extension}" -t "${target_without_ext}_encoded${extension}" -m "$4" --field "$field"
    else
      python3 "$SCRIPT_DIR/main.py" mt_deduplication -s "${source_without_ext}_encoded${extension}" -t "${target_without_ext}_encoded${extension}" -m "$4"
    fi

    # echo "Running quelingua language filtering using SOURCE file..."
    # if [ "$4" = "jsonl" ]; then
    #   python3 "$SCRIPT_DIR/main.py" mt_quelingua -s "${source_without_ext}_encoded_deduplicated${extension}" -t "${target_without_ext}_encoded_deduplicated${extension}" -m "$4" --field "$field" -cl gl -ot "_quelingua"
    # else
    #   python3 "$SCRIPT_DIR/main.py" mt_quelingua -s "${source_without_ext}_encoded_deduplicated${extension}" -t "${target_without_ext}_encoded_deduplicated${extension}" -m "$4" -cl gl -ot "_quelingua"
    # fi

    echo "Running normalization on the new GL file..."
    if [ "$4" = "jsonl" ]; then
      python3 "$SCRIPT_DIR/main.py" normalize --path "${source_without_ext}_encoded_deduplicated${extension}" -o "${source_without_ext}_encoded_deduplicated_quelingua_normalized${extension}" -m "$4" --jsonl_field "$field" --no-detokenize
    else
      python3 "$SCRIPT_DIR/main.py" normalize --path "${source_without_ext}_encoded_deduplicated${extension}" -o "${source_without_ext}_encoded_deduplicated_quelingua_normalized${extension}" -m "$4" --no-detokenize
    fi
    
    echo "Renaming final output files..."
    mv "${source_without_ext}_encoded_deduplicated_quelingua_normalized${extension}" "${source_without_ext}_final${extension}"
    mv "${target_without_ext}_encoded_deduplicated${extension}" "${target_without_ext}_final${extension}"

    echo "MT GL-X parallel pipeline finished."

else
  echo "Running "$SCRIPT_DIR/main.py" with arguments: $@"
  python3 "$SCRIPT_DIR/main.py" "$@"
fi