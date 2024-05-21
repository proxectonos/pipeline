import argparse
from datasketch import MinHash, MinHashLSH
from tqdm import tqdm
import json
import os
from typing import List, Dict, Any, Optional, Tuple, Union
from itertools import islice

def read_documents(filename: str, max_documents: Optional[int] = None, batch_size: int = 1000, input_format: str = 'jsonl') -> List[Dict[str, Any]]:
    def read_batch():
        with open(filename, 'r', encoding='utf-8') as file:
            if input_format == 'jsonl':
                for line in file:
                    yield json.loads(line)
            elif input_format == 'txt':
                content = file.read()
                items = content.split('\n\n')
                for i, item_text in enumerate(items):
                    yield {"text": item_text, "id": i + 1}

    documents = []
    batch_generator = read_batch()
    while True:
        batch = list(islice(batch_generator, batch_size))
        if not batch:
            break
        documents.extend(batch)
        if max_documents and len(documents) >= max_documents:
            break

    return documents


def write_documents(documents: List[Dict[str, Any]], filename: str, output_format: str = 'jsonl') -> None:
    with open(filename, 'w', encoding='utf-8') as file:
        if output_format == 'jsonl':
            for doc in documents:
                file.write(json.dumps(doc, ensure_ascii=False) + '\n')
        elif output_format == 'txt':
            for doc in documents:
                file.write(doc["text"] + '\n\n')

def create_minhash_signature(item: Dict[str, Any], num_perm: int = 128) -> MinHash:
    text = item.get("text", "")
    minhash = MinHash(num_perm=num_perm)
    for word in text.split():
        minhash.update(word.encode('utf-8'))
    return minhash

def find_similar_documents_minhash_dynamic_threshold(
        documents: List[Dict[str, Any]],
        length_threshold: int = 3,
        output_file: Optional[Union[bool, str]] = False,
        max_documents: Optional[int] = None,
        lsh_threshold: float = 0.8,
        generate_deduplication_samples: bool = False,
        args: Optional[argparse.Namespace] = None
) -> Tuple[int, int, int]:
    num_perm = 128

    if max_documents is not None:
        documents = documents[:max_documents]

    minhash_signatures = [create_minhash_signature(doc, num_perm) for doc in tqdm(documents, desc="Creating Minhash signatures")]

    lsh = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)

    for i, signature in enumerate(minhash_signatures):
        lsh.insert(str(i), signature)

    similar_doc_groups = {}

    for i, signature in tqdm(enumerate(minhash_signatures), total=len(minhash_signatures), desc="Finding similar documents with LSH"):
        candidate_results = lsh.query(signature)
        for j in candidate_results:
            j = int(j)
            if i < j:
                len_i = len(documents[i]["text"])
                len_j = len(documents[j]["text"])

                if len_i > 0 and len_j > 0:
                    jaccard_similarity = signature.jaccard(minhash_signatures[j])
                    if jaccard_similarity > (length_threshold / min(len_i, len_j)):
                        if i not in similar_doc_groups:
                            similar_doc_groups[i] = [i, j]
                        else:
                            similar_doc_groups[i].append(j)

    # List of documents to keep and remove
    to_remove = set()
    best_documents = set()

    # Counter for tracking removed documents
    documents_removed_counter = 0

    # Set to keep track of all documents in groups for accurate removal counting
    all_docs_in_groups = set()
    input_filename = os.path.splitext(os.path.basename(args.path))[0]

    for group in similar_doc_groups.values():
        # Find the best document in each group (shortest one by lines)
        best_doc_id = min(group, key=lambda doc_id: len(documents[doc_id]["text"].split('\n')))
        best_documents.add(best_doc_id)

        # Add other documents in the group to the removal list and all_docs_in_groups set
        to_remove.update(doc_id for doc_id in group if doc_id != best_doc_id)
        all_docs_in_groups.update(group)

    # Increment the counter for each document in all_docs_in_groups (excluding the best documents)
    documents_removed_counter = len(all_docs_in_groups) - len(best_documents)

    # Stream write the remaining documents
    deduplicated_documents_path = None
    if output_file:
        deduplicated_documents_path = os.path.join(os.path.dirname(args.path), f"{input_filename}_deduplicated_jaccard.{args.mode}")
        with open(deduplicated_documents_path, 'w', encoding='utf-8') as file:
            if args.mode == 'jsonl':
                for best_doc_id in best_documents:
                    file.write(json.dumps(documents[best_doc_id], ensure_ascii=False) + '\n')
                for i in range(len(documents)):
                    if i not in to_remove and i not in best_documents:
                        file.write(json.dumps(documents[i], ensure_ascii=False) + '\n')
            elif args.mode == 'txt':
                for best_doc_id in best_documents:
                    file.write(documents[best_doc_id]["text"] + '\n\n')
                for i in range(len(documents)):
                    if i not in to_remove and i not in best_documents:
                        file.write(documents[i]["text"] + '\n\n')

    # Generate deduplication samples file name
    if generate_deduplication_samples:
        deduplication_samples_file = os.path.join(os.path.dirname(args.path), f"{input_filename}_deduplicated_jaccard_samples.{args.mode}")
        with open(deduplication_samples_file, 'w') as deduplication_file:
            if args.mode == 'jsonl':
                print("Writing deduplication samples to JSONL file...")  # Debug print
                for group in similar_doc_groups.values():
                    group_data = {
                        "group_ids": [doc_id + 1 for doc_id in group],
                        "best_document_id": min(group, key=lambda doc_id: len(documents[doc_id]["text"].split('\n'))) + 1,
                        "documents": [
                            {
                                "document_id": doc_id + 1,
                                "text": documents[doc_id]["text"],
                                "jaccard_similarity": minhash_signatures[group[0]].jaccard(minhash_signatures[doc_id])
                            } for doc_id in group
                        ]
                    }
                    deduplication_file.write(json.dumps(group_data, ensure_ascii=False) + '\n')
                print("Deduplication samples successfully written to JSONL file.")  # Debug print

            elif args.mode == 'txt':
                for group in similar_doc_groups.values():
                    best_doc_id = min(group, key=lambda doc_id: len(documents[doc_id]["text"].split('\n')))
                    deduplication_file.write(f"Group IDs: {', '.join(str(doc_id + 1) for doc_id in group)}\n")
                    deduplication_file.write(f"Best Document: {best_doc_id + 1}\n\n")
                    deduplication_file.write("Documents:\n\n")
                    for doc_id in group:
                        deduplication_file.write(f"Document id: {doc_id + 1}\n")
                        deduplication_file.write(f"{documents[doc_id]['text']}\n\n")
                        deduplication_file.write(f"Jaccard Similarity with Best Document: {minhash_signatures[best_doc_id].jaccard(minhash_signatures[doc_id]):.2f}\n\n")
                    deduplication_file.write("----------------------------------------\n\n")

    # Return the total number of documents in the file, total deduplicated documents, and count of documents removed
    total_documents_in_file = len(documents)
    total_documents_after_deduplication = total_documents_in_file - documents_removed_counter
    total_documents_removed = documents_removed_counter

    return total_documents_in_file, total_documents_removed, total_documents_after_deduplication


def jaccard_deduplicate(args):
    try:
        total_documents_in_file, total_documents_removed, total_documents_after_deduplication = find_similar_documents_minhash_dynamic_threshold(
            read_documents(args.path, max_documents=args.max_documents, batch_size=1000, input_format=args.mode),
            length_threshold=args.length_threshold,
            output_file=args.output_file,
            lsh_threshold=args.lsh_threshold,
            generate_deduplication_samples=args.generate_deduplication_samples,
            args=args
        )

        print(f'Total documents in the file: {total_documents_in_file}')
        print(f'Total documents deduplicated/removed: {total_documents_removed}')
        print(f'Total documents after deduplication: {total_documents_after_deduplication}')

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    jaccard_deduplicate()
