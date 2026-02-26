import argparse
from inspect import getmembers, isfunction
from methods import subprocesses

class ListMethodsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        print(getmembers(subprocesses, isfunction))
        print(help(subprocesses))
        parser.exit()

def build_parser(handlers):
    """
    Builds the argument parser and maps handlers to subcommands.
    :param handlers: A dictionary mapping action names to function objects.
    """
    parser = argparse.ArgumentParser(description="Nós NLP pipeline.")
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument("--mode", "-m", default="jsonl", help=".txt or .jsonl output format")
    
    parser.add_argument("-lm", "--list_methods", nargs=0, action=ListMethodsAction)
    parser.add_argument("--eol", help="convert EOL to linux format", action=argparse.BooleanOptionalAction)

    subparsers = parser.add_subparsers(dest="action", help="choose one")

    # 1. MT Quelingua
    p = subparsers.add_parser("mt_quelingua", parents=[base_parser])
    p.add_argument("-s", "--source", type=str, required=True)
    p.add_argument("-t", "--target", type=str, required=True)
    p.add_argument("-cl", "--correct_lang_source", type=str, required=True)
    p.add_argument("-ot", "--output_tag", type=str, required=False, default="_quelingua")
    p.set_defaults(func=handlers['mt_quelingua'])

    # 2. Formatter
    p = subparsers.add_parser("formatter", parents=[base_parser])
    p.add_argument("-o", "--output", type=str, required=True)
    p.add_argument("--path", "-p", required=True)
    p.add_argument("-t", "--technique", default="regex")
    p.add_argument("-d", "--delimiter", default="\n\n\n")
    p.set_defaults(func=handlers['formatter'])

    # 3. Pipeline Tasks
    pipeline_cmds = ["encoder", "tokenizer", "detokenizer", "filter_lang", "pyplexity", "mt_transliteration"]
    for cmd in pipeline_cmds:
        p = subparsers.add_parser(cmd, parents=[base_parser])
        p.add_argument("--path", "-p", required=True)
        p.add_argument("-o", "--output", required=True)
        
        if cmd == "encoder":
            p.add_argument("-cat", "--categories", default=[])
            p.add_argument("-char", "--characters", default="")
            p.add_argument("-rmchar", "--remove-characters", default="")
            p.add_argument("-emo", "--emojies", action=argparse.BooleanOptionalAction, default=False)
        elif cmd == "filter_lang":
            p.add_argument("-f", "--filter_results_by_lang", default=False)
        elif cmd == "pyplexity":
            p.add_argument("-pm", "--path_model", default="./models/bigrams_modelo-gl-bigramas-merged.st")
            p.add_argument("-s", "--score", action=argparse.BooleanOptionalAction, default=True)
            p.add_argument("-pl", "--perpl_limit", type=int, default=2000)
            p.add_argument("-r", "--remove_low_scores", action=argparse.BooleanOptionalAction, default=True)
            p.add_argument("pyplexity_args", nargs=argparse.REMAINDER)
        elif cmd == "mt_transliteration":
            p.add_argument("-q", "--quelingua", action=argparse.BooleanOptionalAction, default=False)
            p.add_argument("-f", "--field", default=None, help="Field name for jsonl files")
            #p.set_defaults(func=handlers['mt_transliteration'])

        p.set_defaults(func=handlers['pipeline'])

    # 4. Direct Tools
    p = subparsers.add_parser("normalize", parents=[base_parser])
    p.add_argument("-p", "--path", required=True)
    p.add_argument("--detokenize", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--jsonl_field", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("-b", "--bel", action=argparse.BooleanOptionalAction ,default=False)
    p.add_argument("-e", "--exact", action=argparse.BooleanOptionalAction ,default=False)
    p.set_defaults(func=handlers['normalize'])
    
    p = subparsers.add_parser("recoglang", parents=[base_parser])
    p.add_argument("-p", "--path", required=True)
    p.set_defaults(func=handlers['recoglang'])

    p = subparsers.add_parser("fix_new_lines")
    p.add_argument("-p", "--path", required=True)
    p.set_defaults(func=handlers['fix_newlines'])

    p = subparsers.add_parser("jaccard", parents=[base_parser])
    p.add_argument("-p", "--path", required=True)
    p.add_argument("-o", "--output_file", action='store_true')
    p.add_argument("-md", "--max_documents", type=int)
    p.add_argument("-lt", "--length_threshold", type=int, default=3)
    p.add_argument("-lsh", "--lsh_threshold", type=float, default=0.8)
    p.add_argument("-gds", "--generate_deduplication_samples", action="store_true")
    p.set_defaults(func=handlers['jaccard'])

    p = subparsers.add_parser("deduplication", parents=[base_parser])
    p.add_argument("-p", "--path", required=True)
    p.add_argument("-o", "--output")
    p.add_argument("-ilf", "--input_lf", type=int, default=3)
    p.add_argument("-olf", "--output_lf", type=int, default=2)
    p.add_argument("-t", "--threshold", type=int, default=15)
    p.add_argument("-s", "--save_duplicates", action=argparse.BooleanOptionalAction, default=False)
    p.set_defaults(func=handlers['deduplication'])

    p = subparsers.add_parser("mt_deduplication", parents=[base_parser])
    p.add_argument("-s", "--source", required=True)
    p.add_argument("-t", "--target", required=True)
    p.add_argument("-f", "--field", default=None, help="Field name for jsonl files")
    p.add_argument("-d", "--save_duplicates", action=argparse.BooleanOptionalAction, default=False)
    p.set_defaults(func=handlers['mt_deduplication'])

    '''    p = subparsers.add_parser("mt_transliteration", parents=[base_parser])
        p.add_argument("-p", "--path", required=True)
        p.add_argument("-o", "--output", required=True)
        p.add_argument("-q", "--quelingua", action=argparse.BooleanOptionalAction, default=False)
        p.add_argument("-f", "--field", default=None, help="Field name for jsonl files")
        p.set_defaults(func=handlers['mt_transliteration'])
    '''

    return parser