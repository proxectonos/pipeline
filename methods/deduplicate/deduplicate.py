#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Elimina documentos duplicados utilizando hashes MD5
"""
import argparse
import hashlib
import sys
from .corpus_documents import CorpusDocumentsJSONLine, CorpusDocumentsNewlines


def count_words(doc):
    """
    Count number of words (=blank space separated strings) in a document
    """
    return len(doc.split())


def run(args):
    """
    main function
    """
    seen = set()
    num_doc = None
    unique = 0
    short = 0

    if args.mode == "jsonl":
        docu = CorpusDocumentsJSONLine(field="text")
    else:
        docu = CorpusDocumentsNewlines(
            input_lf=args.input_lf,
            output_lf=args.output_lf
        )
        
    with open(args.output, 'w') as output_file:
        with open(f"{args.output}_removed_deduplicated.jsonl", 'w') as removed_file:
            for num_doc, doc in enumerate(docu.read_file(args.path), start=1):
                if count_words(doc['text']) < args.threshold:
                    short += 1
                    removed_file.write(docu.get_document(doc)+"\n")
                    continue

                hash_md5 = hashlib.md5(doc['text'].encode()).hexdigest()
                if hash_md5 not in seen:
                    unique += 1
                    #print(docu.get_document(doc), end="")
                    output_file.write(docu.get_document(doc)+"\n")
                    seen.add(hash_md5)
                elif args.save_duplicates:
                    removed_file.write(docu.get_document(doc)+"\n")
            print(
                f"{num_doc} documents processed, {short} removed, {unique} unique",
                file=sys.stderr
            )


if __name__ == "__main__":
    run()
