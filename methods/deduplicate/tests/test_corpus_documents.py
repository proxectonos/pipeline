import os
import sys
import pytest
from corpus_documents import CorpusDocumentsNewlines, CorpusDocumentsJSONLine


@pytest.fixture(scope="session")
def lfdoc():
    return CorpusDocumentsNewlines()


@pytest.fixture(scope="session")
def lfdoc_two_lf_in_one_lf_out():
    return CorpusDocumentsNewlines(input_lf=2, output_lf=1, warn=True)


@pytest.fixture(scope="session")
def jsondoc():
    return CorpusDocumentsJSONLine()


@pytest.fixture()
def corpus_filename(tmpdir):
    def _build_corpus_file(contents):
        filename = os.path.join(tmpdir.strpath, 'sample.txt')
        with open(filename, "w") as fhi:
            fhi.write(contents)
        return filename
    return _build_corpus_file


@pytest.fixture()
def jsonl_file(jsondoc, corpus_filename, json_sample_docs):
    return corpus_filename(json_sample_docs)


@pytest.fixture()
def newline_file(lfdoc, corpus_filename, newline_sample_docs):
    return corpus_filename(newline_sample_docs)


@pytest.fixture()
def newline_file_not_normalized(
        lfdoc, corpus_filename, newline_docs_not_normalized):
    return corpus_filename(newline_docs_not_normalized)


def test_get_jsonl_documents_default(
        jsondoc, jsonl_file, json_expected_default):
    for num, doc in enumerate(jsondoc.read_file(jsonl_file)):
        assert doc == json_expected_default[num]


def test_get_newline_documents_default(
        lfdoc, newline_file, newline_expected_default):
    for num, doc in enumerate(lfdoc.read_file(newline_file)):
        assert doc == newline_expected_default[num]


def test_get_newline_documents_two_lf_in_one_lf_out(
        lfdoc_two_lf_in_one_lf_out,
        newline_file,
        newline_expected_two_lf_in_one_lf_out):
    for num, doc in enumerate(lfdoc_two_lf_in_one_lf_out.read_file(newline_file)):
        assert doc == newline_expected_two_lf_in_one_lf_out[num]


def test_get_newline_documents_normalized(
        lfdoc,
        newline_file_not_normalized,
        newline_expected_normalized):
    for num, doc in enumerate(lfdoc.read_file(newline_file_not_normalized)):
        assert doc == newline_expected_normalized[num]
