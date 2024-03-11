import argparse
from methods import subprocesses
from inspect import getmembers, isfunction

class List_methods(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        print(getmembers(subprocesses, isfunction))
        print(help(subprocesses))
        parser.exit()  # exits the program with no more arg parsing and checking

def _build_parser():
    parser = argparse.ArgumentParser(
        description="Nós NLP pipeline.",
        epilog="See '<command> --help' to read about a specific sub-command. e.g. tokenizer --help",
    )

    base_parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-lm", "--list_methods", nargs=0, action=List_methods)

    parser.add_argument("--eol", help='convert end of line sequence to linux format', action=argparse.BooleanOptionalAction)

    subparsers = parser.add_subparsers(dest="action", help="choose one")
    
    formatter_parser = subparsers.add_parser(
        "formatter", help="Process a text file and create a JSON lines file.", parents=[base_parser]
    )
    formatter_parser.add_argument('-i','--input', type=str, help='Absolute path to the input')
    formatter_parser.add_argument('-m','--method', choices=['regex', 'folder'], type=str, help='method used to split the corpus into documents')
    formatter_parser.add_argument('-o','--output', type=str, help='Path to the output JSON lines file')
    formatter_parser.add_argument( 
        "-pattern",
        "--p",
        type=str,
        required=True,
        help="regex patter to divide an input into documents when using the pattern heuristic",
    )

    encoder_parser = subparsers.add_parser(
        "encoder", help="encode plain text file to utf-8", parents=[base_parser]
    )
    encoder_parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="absolute path to text file to encode",
    )
    encoder_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file absolute path"
    )
    encoder_parser.add_argument(
        "-cat",
        "--categories",
        type=str,
        help='In personalized filter, specify the unicode categories required for filtering the data (e.g. "Lu Lm Ll Lt"). You can see all the available categories here: https://pypi.org/project/unicategories/',
        default=[],
    )
    encoder_parser.add_argument(
        "-char",
        "--characters",
        type=str,
        help="Specify in a string the characters you want to mantein in the data.",
        default="",
    )
    encoder_parser.add_argument(
        "-rmchar",
        "--remove-characters",
        type=str,
        help="Specify in a string the characters you want to remove in the data.",
        default="",
    )
    encoder_parser.add_argument(
        "-emo",
        "--emojies",
        type=bool,
        help="Boolean. In personalized filter, True value for keeping the emojies in the text. Otherwise, False",
        default=False,
    )

    tokenizer_parser = subparsers.add_parser(
        "tokenizer", help="tokenize plain text file", parents=[base_parser]
    )
    tokenizer_parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="absolute path to text file to tokenize",
    )
    tokenizer_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file absolute path"
    )

    detokenizer_parser = subparsers.add_parser(
        "detokenizer",
        help="detokenize text file tokenized with our tokenizer",
        parents=[base_parser],
    )
    detokenizer_parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="absolute path to text file to detokenize",
    )
    detokenizer_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file absolute path"
    )

    recoglang_parser = subparsers.add_parser(
        "recoglang", help="identify the language a text is written in"
    )
    recoglang_parser.add_argument(
        "-p", "--path", type=str, required=True, help="path to source file"
    )

    filter_lang_parser = subparsers.add_parser(
        "filter_lang",
        help="returns all text in the source file that matches the specified target language",
    )
    filter_lang_parser.add_argument(
        "-p", "--path", type=str, required=True, help="path to source file"
    )
    filter_lang_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file path"
    )
    filter_lang_parser.add_argument(
        "-f",
        "--filter_results_by_lang",
        type=str,
        default=False,
        required=False,
        help="If specified, filter file by lang",
    )
    fix_new_lines_parser = subparsers.add_parser(
        "fix_new_lines",
        help="returns all text in the source file that matches the specified target language",
    )
    fix_new_lines_parser.add_argument(
        "-p", "--path", type=str, required=True, help="path to source file"
    )
    jaccard_similarity_parser = subparsers.add_parser(
        "jaccard", help="deduplicate files with jaccard similarity", parents=[base_parser]
    )
    jaccard_similarity_parser.add_argument("input_file","-i", help="Path to the input JSONL file.")
    jaccard_similarity_parser.add_argument("--input_format", "-if", choices=['jsonl', 'txt'], default='jsonl', help="Specify the format of the input file (jsonl or txt). Default is jsonl.")
    jaccard_similarity_parser.add_argument("--output_file", "-o", action="store_true", help="Generate deduplicated file at the same folder as the input file.")
    jaccard_similarity_parser.add_argument("--output_format", "-of", choices=['jsonl', 'txt'], default='jsonl', help="Specify the format for the deduplicated output file (jsonl or txt). Default is jsonl.")
    jaccard_similarity_parser.add_argument("--max_documents", "-md",  type=int, help="Set the maximum number of documents to process if necessary. If not flagged, it will process all documents.")
    jaccard_similarity_parser.add_argument("--length_threshold", "-lt", type=int, default=3, help="Set length threshold for similarity comparison. Default is 3. Adjust with lower values especially if texts to deduplicate have different lengths. Adjust with higher values if you want a stricter comparison.")
    jaccard_similarity_parser.add_argument("--lsh_threshold", "-lsh", type=float, default=0.8, help="Set LSH threshold for similarity comparison. Default is 0.8. Higher values are more strict to consider similarities.")
    jaccard_similarity_parser.add_argument("--generate_deduplication_samples", "-gds", action="store_true", help="Generate deduplication samples for manual inspection. This combined with --max_documents can generate the required samples before deduplicating the whole file, ex: path/to/input/file -md 20000 -gds. File will be saved at the same folder as the input file")
    jaccard_similarity_parser.add_argument("--samples_format", "-sf", choices=['json', 'txt'], default='json', help="Specify the format for the deduplication samples file (json or txt). Default is json.")
    
    deduplication_parser = subparsers.add_parser(
        "deduplication", help="deduplicate files with hashes", parents=[base_parser]
    )
    deduplication_parser.add_argument("ifile", type=str, help="Input file")
    deduplication_parser.add_argument(
        "-ilf",
        "--input_lf",
        default=3,
        type=int,
        help="Number of LF as document separator for the input corpus (only for format=newlines)",
    )
    deduplication_parser.add_argument(
        "-olf",
        "--output_lf",
        default=2,
        type=int,
        help="Number of LF as document separator for the output corpus (only for format=newlines)",
    )
    deduplication_parser.add_argument(
        "-t",
        "--threshold",
        default=15,
        type=int,
        help="Documents with number of words < THRESHOLD will be removed",
    )
    deduplication_parser.add_argument(
        "-f",
        "--format",
        default="jsonl",
        type=str,
        choices=["jsonl", "newlines"],
        help="Input format",
    )

    return parser.parse_args()