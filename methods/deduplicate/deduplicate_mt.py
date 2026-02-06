import hashlib
import json
import os 
from pathlib import Path

def parallel_deduplicate(file_to_process: str, parallel_file: str, file_type: str = "text", field: str = None):
    if file_type == "jsonl" and field is None:
        raise ValueError("field parameter is required when file_type is 'jsonl'")
    
    seen = set()
    # Using a set for lookups later
    to_remove = set() 
    
    # Get output file paths
    source_path = Path(file_to_process)
    target_path = Path(parallel_file)
    
    source_output = source_path.parent / f"{source_path.stem}_deduplicated{source_path.suffix}"
    target_output = target_path.parent / f"{target_path.stem}_deduplicated{target_path.suffix}"
    
    # Process source file
    with open(file_to_process, "r", encoding="utf-8") as ftp, \
         open(source_output, "w", encoding="utf-8") as temp:
        
        for i, line in enumerate(ftp):
            # Determine what to hash based on file type
            if file_type == "jsonl":
                try:
                    data = json.loads(line)
                    content_to_hash = str(data.get(field, ""))
                except json.JSONDecodeError:
                    continue # Skip malformed lines
            else:
                content_to_hash = line

            line_hash = hashlib.blake2b(content_to_hash.encode('utf-8'), digest_size=16).digest()
            
            if line_hash not in seen:
                seen.add(line_hash)
                temp.write(line) # Writes the ORIGINAL line (full JSON or full text)
            else:
                to_remove.add(i)


    with open(file_to_process, "r", encoding="utf-8") as og, \
        open(source_output, "w", encoding="utf-8") as out_src:
        for i, line in enumerate(og):
            if i not in to_remove:
                out_src.write(line)

    # Process the parallel file
    with open(parallel_file, "r", encoding="utf-8") as parallel, \
         open(target_output, "w", encoding="utf-8") as out_tgt:
        for i, line in enumerate(parallel):
            if i not in to_remove:
                out_tgt.write(line)

    print(f"Deduplication complete. Removed {len(to_remove)} lines.")
    print(f"Source output: {source_output}")
    print(f"Target output: {target_output}")


if __name__ == "__main__":
    parallel_deduplicate("dgt.gl", "dgt.pt", file_type="txt")