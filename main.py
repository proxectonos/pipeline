from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
from methods.deduplicate import deduplicate
from methods.jaccardsimilarity_deduplication import jaccard_deduplicate
from methods.fix_newlines import fix_newlines_doc
from methods.encoder.fixer import encoding_fixer
from inspect import getmembers, isfunction
from methods.formatter import main as formatter
from methods import subprocesses
from methods.normalize import extract_rules, process_file
import codecs
from multiprocessing import Process
from pathlib import Path
from tqdm import tqdm
from operator import itemgetter
import argparse
import shutil
import glob
import json
import mmap
import sys
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
action = None
NUM_FILES = 4


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
    base_parser.add_argument(
        "--mode", "-m", default="jsonl", help=".txt or .jsonl output format"
    )

    parser.add_argument("-lm", "--list_methods", nargs=0, action=List_methods)

    parser.add_argument(
        "--eol",
        help="convert end of line sequence to linux format",
        action=argparse.BooleanOptionalAction,
    )

    subparsers = parser.add_subparsers(dest="action", help="choose one")

    mt_quelingua_parser = subparsers.add_parser(
        "mt_quelingua", help="check line by line if the data is in the correct language. Filters input to return only ", parents=[base_parser]
    )

    mt_quelingua_parser.add_argument(
        "-ot", "--output_tag", type=str, required=True, help="output tag to append to file e.g. $filename.quelingua"
    )
    mt_quelingua_parser.add_argument("-s", "--source", type=str, required=True, help="source file absolute path")
    mt_quelingua_parser.add_argument("-t", "--target", type=str, required=True, help="target file absolute path")
    mt_quelingua_parser.add_argument("-cl", "--correct_lang_source", type=str, required=True, help="correct expected language tag for each line in the source file")

    formatter_parser = subparsers.add_parser(
        "formatter", help="format a file into jsonl format", parents=[base_parser]
    )

    formatter_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file absolute path"
    )
    formatter_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )
    formatter_parser.add_argument(
        "-t",
        "--technique",
        type=str,
        help="Default: regex. Select technique to transformer input data into jsonl files",
        default="regex",
    )
    # -d $'\n\t's
    formatter_parser.add_argument(
        "-d",
        "--delimiter",
        type=str,
        help="Default:\n\n\n. regex arguments must be preceded by $ e.g. #-d $'#\|\|\|#\n\n\n' ",
        default="\n\n\n",
    )
    
    encoder_parser = subparsers.add_parser(
        "encoder", help="encode plain text file to utf-8", parents=[base_parser]
    )
    encoder_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
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
        action=argparse.BooleanOptionalAction,
        help="Boolean. In personalized filter, True value for keeping the emojies in the text. Otherwise, False",
        default=False,
    )

    tokenizer_parser = subparsers.add_parser(
        "tokenizer", help="tokenize plain text file", parents=[base_parser]
    )
    tokenizer_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
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
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )
    detokenizer_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file absolute path"
    )

    recoglang_parser = subparsers.add_parser(
        "recoglang", help="identify the language a text is written in", parents=[base_parser]
    )
    recoglang_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )
    filter_lang_parser = subparsers.add_parser(
        "filter_lang",
        parents=[base_parser],
        help="returns all text in the source file that matches the specified target language",
    )
    filter_lang_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
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
        help="If specified, filter file by lang tag e.g. gl, es, en, pt, etc.",
    )
    fix_new_lines_parser = subparsers.add_parser(
        "fix_new_lines",
        help="fixes number of new lines between documents to 3",
    )
    fix_new_lines_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )

    jaccard_similarity_parser = subparsers.add_parser(
        "jaccard",
        help="deduplicate files with jaccard similarity",
        parents=[base_parser],
    )
    jaccard_similarity_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )
    jaccard_similarity_parser.add_argument(
        "--output_file",
        "-o",
        required=False,
        action='store_true',
        help="Generate deduplicated file at the same folder as the input file.",
    )

    jaccard_similarity_parser.add_argument(
        "--max_documents",
        "-md",
        type=int,
        help="Set the maximum number of documents to process if necessary. If not flagged, it will process all documents.",
    )
    jaccard_similarity_parser.add_argument(
        "--length_threshold",
        "-lt",
        type=int,
        default=3,
        help="Set length threshold for similarity comparison. Default is 3. Adjust with lower values especially if texts to deduplicate have different lengths. Adjust with higher values if you want a stricter comparison.",
    )
    jaccard_similarity_parser.add_argument(
        "--lsh_threshold",
        "-lsh",
        type=float,
        default=0.8,
        help="Set LSH threshold for similarity comparison. Default is 0.8. Higher values are more strict to consider similarities.",
    )
    jaccard_similarity_parser.add_argument(
        "--generate_deduplication_samples",
        "-gds",
        required=False,
        action="store_true",
        help="Generate deduplication samples for manual inspection. This combined with --max_documents can generate the required samples before deduplicating the whole file, ex: path/to/input/file -md 20000 -gds. File will be saved at the same folder as the input file",
    )

    deduplication_parser = subparsers.add_parser(
        "deduplication", help="deduplicate files with hashes", parents=[base_parser]
    )
    deduplication_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )
    deduplication_parser.add_argument(
        "--output", "-o", type=str, help="path to Output file"
    )
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
        required=False,
        type=int,
        nargs="?",
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
        "-s",
        "--save_duplicates",
        type=bool,
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Save duplicates in a separate file",
    )
    pyplexity_parser = subparsers.add_parser(
        "pyplexity",
        help="calculate perplexity of a language model",
        parents=[base_parser],
    )
    pyplexity_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )
    pyplexity_parser.add_argument(
        "--path_model",
        "-pm",
        type=str,
        help="path to perplexity model ",
        default="./models/bigrams_modelo-gl-bigramas-merged.st",
    )
    pyplexity_parser.add_argument(
        "--score",
        "-s",
        type=bool,
        action=argparse.BooleanOptionalAction,
        help="simply return perplexity score. No text modifications.",
        default=True,
    )
    # pyplexity_parser.add_argument(
    #     "--html_cleaning",
    #     "-html",
    #     type=bool,
    #     action=argparse.BooleanOptionalAction,
    #     help="enable HTMLTagRemover to extract text from html files",
    #     default=False,
    # )
    # pyplexity_parser.add_argument(
    #     "--text_cleaning",
    #     "-text",
    #     type=bool,
    #     action=argparse.BooleanOptionalAction,
    #     help="jsonl only.  clean text files that may include abnormal parts e.g. text in different languages, scripts, etc. The result is saved in a separate key.",
    #     default=True,
    # )
    pyplexity_parser.add_argument(
        "--perpl_limit",
        "-pl",
        type=int,
        help="perplexity limit. Threshold for perplexity score.",
        default=2000,
    )
    pyplexity_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file path"
    )
    pyplexity_parser.add_argument(
        "-r",
        "--remove_low_scores",
        type=bool,
        action=argparse.BooleanOptionalAction,
        default=True,
        help="remove documents with a threshold beyond the specified limit",
    )
    pyplexity_parser.add_argument("pyplexity_args", nargs=argparse.REMAINDER)

    normalize_parser = subparsers.add_parser(
        "normalize", help="normalize galician language text files", parents=[base_parser]
    )
    normalize_parser.add_argument(
        "--path", "-p", required=True, type=str, help="Absolute path to Input file"
    )
    normalize_parser.add_argument(
        "-o", "--output", type=str, required=True, help="output file absolute path"
    )
    normalize_parser.add_argument(
        "--detokenize",
        type=bool,
        action=argparse.BooleanOptionalAction,
        help="detokenize the text before normalization",
        default=False,
    )
    normalize_parser.add_argument(
        "--jsonl_field",
        type=str,
        help="if input is jsonl, specify the field to normalize",
        default="text",
        required=False,
    )

    return parser


def convert_to_lf(input_file):
    """
    convert always to linux LF
    """
    # replacement strings
    WINDOWS_LINE_ENDING = b"\r\n"
    UNIX_LINE_ENDING = b"\n"

    with open(input_file, "rb") as open_file:
        with open(f"{input_file}_lf", "wb") as out_file:
            for content in open_file:
                # Windows ➡ Unix
                content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)
                # Unix ➡ Windows
                # content = content.replace(UNIX_LINE_ENDING, WINDOWS_LINE_ENDING)
                out_file.write(content)

    return f"{input_file}_lf"


def process_line(line, action, args):
    processed_line = None
    if action == "tokenizer":
        processed_line = subprocesses.tokenizer_paulo(line)
    elif action == "detokenizer":
        processed_line = subprocesses.detokenizer_paulo(line)
    elif action == "encoder":
        processed_line = encoding_fixer(
            text=line,
            filtered_categories=args.categories,
            filtered_characters=args.characters,
            remove_characters=args.remove_characters,
            emojies=args.emojies,
        )
    return processed_line


def process_line_shared(line, action, args, shared_lines, idx):
    processed_line = process_line(line, action, args)
    shared_lines[idx] = processed_line


def split_file_chunk(mm, start, lines_to_write, output_file, pbar, extension):

    with open(output_file, "wb") as out:
        for _ in range(lines_to_write):
            line = mm.readline()
            if not line:
                break
            if extension == ".jsonl":
                line = json.loads(line, strict=False)
                #print(line)
                #print(json.dumps(line, ensure_ascii=False))
                #print("="*100)
                out.write(json.dumps(line, ensure_ascii=False).encode("utf-8") + b"\n")
            else:
                out.write(line)
            start = mm.tell()
            pbar.update(1)  # Update the progress bar
        return start


def _split_into_files(args, num_files: int = 2, extension: str = ".jsonl"):
    # split big files into manageable inputs



    Path("./temp/").mkdir(parents=True, exist_ok=True)

    # get the file size
    file_size = os.path.getsize(args.path)

    # calculate lines per file
    with open(args.path, "r", encoding="utf-8", errors="ignore") as f:
        total_lines = sum(1 for _ in f)

    lines_per_file = total_lines // num_files
    remainder = total_lines % num_files

    print(f"Splitting {total_lines} lines into a maximum of {num_files} smaller files")

    with open(args.path, "r", encoding="utf-8", errors="ignore") as f:
        with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mm:
            start = 0
            futures = []

            with ThreadPoolExecutor() as executor:
                pbar = tqdm(
                    total=total_lines
                )  # Initialize the progress bar with the total number of lines
                for i in range(num_files):
                    output_file = f"./temp/{i}{extension}"
                    lines_to_write = lines_per_file + (1 if i < remainder else 0)
                    future = executor.submit(
                        split_file_chunk, mm, start, lines_to_write, output_file, pbar, extension
                    )
                    futures.append(future)
                    start = future.result()

                # Wait for all the tasks to complete
                for future in futures:
                    future.result()

                pbar.close()  # Close the progress bar after all tasks are completed
                print("Done", end='\n')


def _сheck_if_folder(input) -> bool:
    if os.path.isdir(input):
        return True
    else:
        return False


def parallelize(file, args):
    global action
    global lang
    path = os.path.abspath(file)
    if args.action == "filter_lang":
        # subprocesses.quelingua(text=path, _type="whole")
        subprocesses.quelingua_lines(path=path, args=args)
    elif args.action == "pyplexity":
        print("Calculating perplexity", end=' ')
        # print(f'python3 {dir_path}/external/pyplexity/pyplexity.py  {path} {args.pyplexity_args}')
        subprocesses.pyplexity(path=path, args=args)
    elif args.action == "normalize":
        process_file(txt=path, sheets=extract_rules("./data/normalization.xlsx"), detokenize=args.detokenize, output=f"{file}_p", mode=args.mode, jsonl_field=args.jsonl_field)
    else:  # line by line
        with open(f"{file}_p", "w+", encoding="utf-8") as prd:
            with open(file, "r+b") as path_file:
                total_lines = sum(1 for _ in path_file)
                path_file.seek(0)  # Reset the file pointer back to the beginning

                pbar = tqdm(
                    total=total_lines
                )  # Initialize the progress bar with the total number of lines
                m_m = mmap.mmap(path_file.fileno(), 0)

                for line in tqdm(iter(m_m.readline, b""), total=total_lines):
                    if action == "tokenizer":
                        line = subprocesses.tokenizer_paulo(line.decode("utf-8"))
                    elif action == "detokenizer":
                        line = subprocesses.tokenizer_paulo(line.decode("utf-8"))

                    elif action == "encoder":
                        line = encoding_fixer(
                            text=line,
                            filtered_categories=args.categories,
                            filtered_characters=args.characters,
                            remove_characters=args.remove_characters,
                            emojies=args.emojies,
                        )
                    prd.write(f"{line}\n")
                m_m.close()
                pbar.close()  # Close the progress bar after all tasks are completed
        path_file.close()


def run():
    args = _build_parser().parse_args()
    global action
    global NUM_FILES
    # Remove folder if it exists
    if os.path.exists("./temp"):
        shutil.rmtree("./temp")
    action = args.action

    if action == 'mt_quelingua':
        subprocesses.mt_quelingua(args)
        sys.exit()

    if args.action == "formatter":
        args.delimiter = codecs.decode(args.delimiter, 'unicode_escape')

        formatter.run(args.path, args.technique, args.output, args.delimiter)
        sys.exit()

    if args.eol == True:
        print("converting to end of line sequence LF (linux format)")
        args.path = convert_to_lf(args.path)

    if args.mode == "txt":
        extension = ".txt"
    elif args.mode == "jsonl":
        extension = ".jsonl"
    print(f"Expecting \033[1;31m{args.mode}\033[0m input and output format")

    if args.action == "recoglang":
        print(subprocesses.quelingua(text=args.path, _type="whole"))
        sys.exit()
    elif args.action == "fix_new_lines":
        fix_newlines_doc(path=args.path)
        sys.exit()
    elif action == "jaccard":
        jaccard_deduplicate(args)
        sys.exit()
    elif action == "deduplication":
        deduplicate.run(args)
        sys.exit()

    else:  # só para processos que não precisam ter o ficheiro inteiro em memória
        _split_into_files(args=args, num_files=NUM_FILES, extension=extension)
        files = glob.glob(f"./temp/*{extension}")
        processes = []
        print(f"Processing {len(files)} smaller files in parallel")
        for file in files:
            proc = Process(
                target=parallelize,
                args=(
                    file,
                    args,
                ),
            )
            processes.append(proc)
            proc.start()

        # complete the processes
        for proc in processes:
            proc.join()

    if "output" in args:
        print("writing output")
        with open(args.output, "w+", encoding="utf-8", errors="ignore") as tgt_file:
            for file in sorted(
                files, key=lambda x: int(x.split("/")[-1].split(".")[0])
            ):
                with open(f"{file}_p", "r", encoding="utf-8", errors="ignore") as fp:
                    for line in fp.readlines():
                        tgt_file.write(line)

    if "remove_low_scores" in args and args.remove_low_scores:
        output_filename, output_extension = os.path.splitext(args.output)
        output_filename_removed = f"{output_filename}_removed{output_extension}"

        with open(output_filename_removed, "w+", encoding="utf-8", errors="ignore") as tgt_file:
            for file in sorted(
                files, key=lambda x: int(x.split("/")[-1].split(".")[0])
            ):
                if os.path.exists(f"{file}_removed"):
                    with open(f"{file}_removed", "r", encoding="utf-8", errors="ignore") as fp:
                        for line in fp.readlines():
                            tgt_file.write(line)

    shutil.rmtree("./temp")
    # Remove all files that start with "__tmp_" quickfix quelingua tmp files
    for filename in os.listdir("./"):
        if filename.startswith("__tmp_"):
            file_path = os.path.join("./", filename)
            os.remove(file_path)

if __name__ == "__main__":
    run()
