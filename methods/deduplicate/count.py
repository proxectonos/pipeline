#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Conta documentos
"""
import argparse
import glob
import sys
from corpus_documents import CorpusDocumentsNewlines


def parse_args():
    """
    Gere os argumentos da linha de comandos
    """
    description = "Count documents separated with newlines"
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "input_files",
        type=str,
        nargs='+',
        help="Input files",
    )
    parser.add_argument(
        "-i",
        "--input_lf",
        default=2,
        type=int,
        help="Number of LF as document separator for the input corpus (only for format=newlines)",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        default=15,
        type=int,
        help="Documents with number of words < THRESHOLD will be removed",
    )

    return parser.parse_args()


def run():
    """
    main function
    """
    args = parse_args()
    total_docs = 0
    short = 0

    docu = CorpusDocumentsNewlines(
        input_lf=args.input_lf
    )

    for ifile in args.input_files:
        num_docs = 0
        for doc in docu.read_file(ifile):
            if count_words(doc) < args.threshold:
                short += 1
                continue
            num_docs += 1
        print(f"{num_docs} {ifile}", file=sys.stderr)
        total_docs += num_docs

    print(f"\n{total_docs} total documents ({short} removed)", file=sys.stderr)


if __name__ == "__main__":
    run()
