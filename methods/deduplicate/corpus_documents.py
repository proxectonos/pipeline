"""
Classes for processing corpus documents in JSONL format or with documents
separated by newline characters.
"""
import json
import re
import sys


class CorpusDocuments:
    """
    Parent class
    """
    def _normalize_patterns(self, line):
        """
        Apply a list of replacement rules to a line

        TODO
          - These rules could be imported from an external resource
          - Patterns could be compiled
        """
        rules = [
            (r'\-\-+', ' '),
            (r'\. \. \.', ' ')
        ]

        for pattern, replacement in rules:
            line = re.sub(pattern, replacement, line)
        return line

    def _normalize_blanks(self, line):
        """
        Remove extra blank spaces in lines
        """
        return ' '.join(line.split())

    def normalize(self, raw_doc):
        """
        Normalize raw_doc (a document represented as a list of lines)
        """
        raw_doc = [self._normalize_patterns(line) for line in raw_doc]
        raw_doc = [self._normalize_blanks(line) for line in raw_doc]

        return '\n'.join(raw_doc)


class CorpusDocumentsJSONLine(CorpusDocuments):
    """
    Class to process a file in JSONL format
    """
    def __init__(self, field="text"):
        self.field = field

    def read_file(self, ifile):
        """
        Read a JSONL file and returns a generator with the documents
        """
        try:
            with open(ifile, encoding="utf-8") as fhi:
                for num, line in enumerate(fhi, start=1):
                    if not line.strip():
                        continue
                    text = json.loads(line, strict=False)
                    if self.field not in text:
                        raise ValueError(text)
                    yield text
        except ValueError as exc:
            print(
                f"Field '{self.field}' not found in line {num}: {exc}",
                file=sys.stderr)
            sys.exit(3)
        except OSError as exc:
            print(exc, file=sys.stderr)
            sys.exit(2)

    def get_document(self, doc):
        """
        Return a document in JSONL format
        """
        return json.dumps(doc, ensure_ascii=False)


class CorpusDocumentsNewlines(CorpusDocuments):
    """
    Class to process a file with documents separated by newlines
    """
    def __init__(self, warn=False, strict=False, input_lf=3, output_lf=2):
        self.warn = warn
        self.strict = strict
        self.input_lf = input_lf
        self.output_lf = output_lf

    def read_file(self, ifile):
        """
        Read a text file and returns a generator with the documents
        """
        raw_doc = []
        try:
            with open(ifile, encoding="utf-8") as fhi:
                linefeed = 1
                buf = []
                for num, line in enumerate(fhi, start=1):
                    line = line.strip()
                    if line:
                        linefeed = 1
                        if len(buf) > 0 and self.strict:
                            raw_doc.extend(buf)
                            buf = []
                        raw_doc.append(line)
                    else:
                        linefeed += 1
                        if linefeed < self.input_lf:
                            buf.append(line)
                        elif linefeed == self.input_lf and len(raw_doc) > 0:
                            buf = []
                            doc = self.normalize(raw_doc)
                            raw_doc = []
                            yield doc
                        elif linefeed > self.input_lf:
                            if self.warn:
                                print(
                                    "Warning: more than {} linefeed chars "
                                    "between docs in line {}".format(
                                        self.input_lf, num
                                    ),
                                    file=sys.stderr
                                )
                        else:
                            buf = []
                if raw_doc:
                    yield {"id": num, "text":self.normalize(raw_doc)}
        except OSError as exc:
            print(exc, file=sys.stderr)
            sys.exit(2)

    def get_document(self, doc):
        """
        Return a document separated by newlines
        """
        return doc["text"] + self.output_lf * "\n"
