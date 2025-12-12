#!/bin/bash
echo "$@"



if [ $1 = "standard_pipeline" ] 
then
  filepath=$(dirname "$2")
  filename=$(basename "$2" .jsonl)
  fullpath_without_ext="$filepath/$filename"
  echo "Starting standard pipeline..."
  
   echo "Running encoder..."
   python3 main.py encoder -p $2 -o $fullpath_without_ext"_encoded.jsonl"
  
   echo "Running deduplication..."
   python3 main.py deduplication -p $fullpath_without_ext"_encoded.jsonl" -o $fullpath_without_ext"_encoded_deduplicated.jsonl" --save_duplicates
  
   echo "Running pyplexity..."
   python3 main.py pyplexity -p $fullpath_without_ext"_encoded_deduplicated.jsonl" -o $fullpath_without_ext"_encoded_deduplicated_pyplexity.jsonl" --remove_low_scores
  
  echo "Running filter_lang..."
  python3 main.py filter_lang --filter_results_by_lang gl -p $fullpath_without_ext"_encoded_deduplicated_pyplexity.jsonl" -o  $fullpath_without_ext"_encoded_deduplicated_pyplexity_quelingua.jsonl"

  echo "Running normalization..."
  python3 main.py normalize --mode jsonl --path  $fullpath_without_ext"_encoded_deduplicated_pyplexity_quelingua.jsonl" --o  $fullpath_without_ext"_encoded_deduplicated_pyplexity_quelingua_normalized.txt" --no-detokenize

else
  echo "Running main.py with arguments: $@"
  python3 main.py "$@"
fi