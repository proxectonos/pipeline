#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Elimina documentos duplicados utilizando hashes MD5
"""
import argparse
import hashlib
import os
import sys
from corpus_documents import CorpusDocumentsJSONLine, CorpusDocumentsNewlines


MARK = "_dedup"


def parse_args():
    """
    Gere os argumentos da linha de comandos
    """
    description = "Remove duplicated documents using MD5 hashes"
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "input_files",
        type=str,
        nargs='+',
        help="Input file(s)",
    )
    parser.add_argument(
        "-O",
        "--output_dir",
        type=str,
        help="Output directory",
    )
    parser.add_argument(
        "-i",
        "--input_lf",
        default=3,
        type=int,
        help="Number of LF as document separator for the input corpus (only for format=newlines)",
    )
    parser.add_argument(
        "-o",
        "--output_lf",
        default=2,
        type=int,
        help="Number of LF as document separator for the output corpus (only for format=newlines)",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="jsonl",
        type=str,
        choices=["jsonl", "newlines"],
        help="Input format",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        default=15,
        type=int,
        help="Documents with number of words < THRESHOLD will be removed",
    )

    return parser.parse_args()


def get_output_file(ifile, output_dir):
    """
    Obtain the output filename based on the input filename
    """
    root, filename = os.path.split(ifile)
    basefile, ext = os.path.splitext(filename)
    if not output_dir:
        output_dir = root

    return os.path.join(output_dir, f"{basefile}{MARK}{ext}")


def count_words(doc):
    """
    Count number of words (=blank space separated strings) in a document
    """
    return len(doc.split())


def run():
    """
    main function
    """
    args = parse_args()
    seen = set()
    total_docs = 0
    unique = 0
    short = 0

    if args.format == "jsonl":
        docu = CorpusDocumentsJSONLine(field="text")
    else:
        docu = CorpusDocumentsNewlines(
            input_lf=args.input_lf,
            output_lf=args.output_lf
        )

    for ifile in args.input_files:
        ofile = get_output_file(ifile, args.output_dir)
        if os.path.exists(ofile):
            print(f"Error: file exists {ofile}")
            sys.exit(1)
        try:
            with open(ofile, "w", encoding="utf-8") as fho:
                num_doc = 0
                for doc in docu.read_file(ifile):
                    total_docs += 1
                    num_doc += 1
                    if count_words(doc) < args.threshold:
                        short += 1
                        continue

                    hash_md5 = hashlib.md5(doc.encode()).hexdigest()
                    if hash_md5 not in seen:
                        unique += 1
                        print(docu.get_document(doc), end="", file=fho)
                        seen.add(hash_md5)
            print(f"{num_doc} documents processed in {ifile}", file=sys.stderr)
        except OSError as exc:
            print(exc, file=sys.stderr)
            sys.exit(2)

    print(
        f"\n{total_docs} total documents processed, {short} removed, {unique} unique",
        file=sys.stderr
    )


if __name__ == "__main__":
    run()
