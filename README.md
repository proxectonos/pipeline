# Nós NLP Cleaning Pipeline for Galician

This toolkit provides a set of tools and pipelines to clean and process Galician datasets, specifically designed for training Machine Translation (MT) and Large Language Models (LLM). It supports both monolingual and parallel corpora in `.txt` and `.jsonl` formats.

## 🚀 Quick Start

### Installation

1. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Setup external dependencies:**
   ```bash
   ./entrypoint.sh install
   ```
   This will clone the necessary repositories (`port2gal`, `pyplexity`, `QueLingua`) into `methods/external`.

### Usage
The main entry point is `entrypoint.sh`. You can see all available commands by running:
```bash
./entrypoint.sh --help
```

---

## 🛠 Pipeline Modes

### 1. Standard Pipeline (Monolingual)
Cleans a monolingual Galician corpus.
- **Workflow:** Encoding Fix → Deduplication → Perplexity Filtering → Language Filtering → Normalization
- **Commands:**
  ```bash
  ./entrypoint.sh standard_pipeline <input.jsonl|.txt>
  ```
- **Output:** A normalized `.txt` file with the cleaned content.

### 2. MT Pipeline (Parallel)
Cleans a parallel corpus where the source is Galician.
- **Workflow:** Encoding Fix → Parallel Deduplication → FastText Language Filtering → Parallel Pyplexity Filtering → MT Alignment Filtering → Normalization
- **Commands:**
  ```bash
  # For TXT files:
  ./entrypoint.sh mt_pipeline <source_gl.txt> <target.txt> txt
  
  # For JSONL files (specifying the text field):
  ./entrypoint.sh mt_pipeline <source_gl.jsonl> <target.jsonl> jsonl text
  ```

### 3. PT-GL Parallel Pipeline (Transliteration)
Specialized pipeline for Portuguese-to-Galician parallel corpora. It uses Apertium for symbolic translation and `port2gal` for post-processing.
- **Workflow:** Encoding Fix → Parallel Deduplication → Apertium Transliteration → Normalization
- **Requirements:** Docker (image `proxectonos/apertium:3.9.12_custom_marks`)
- **Commands:**
  ```bash
  ./entrypoint.sh PT_GL_parallel <source_pt> <target> <format> [field]
  ```

---

## 🔧 Individual Tools

You can also run individual steps directly through `entrypoint.sh`:

| Tool | Description | Example |
| :--- | :--- | :--- |
| `encoder` | Fixes encoding issues | `./entrypoint.sh encoder -p in.txt -o out.txt` |
| `deduplication` | Removes duplicate documents | `./entrypoint.sh deduplication -p in.jsonl -o out.jsonl` |
| `mt_alignment` | Flags potentially misaligned source-target pairs and writes a report | `./entrypoint.sh mt_alignment -s src.txt -t tgt.txt -m txt` |
| `pyplexity` | Perplexity filtering (Galician model) | `./entrypoint.sh pyplexity -p in.jsonl -o out.jsonl` |
| `filter_lang` | Language filtering (QueLingua) | `./entrypoint.sh filter_lang -p in.jsonl -o out.jsonl` |
| `normalize` | Applies Galician orthographic rules | `./entrypoint.sh normalize -p in.txt -o out.txt` |
| `tokenizer` | Specialized Galician tokenizer | `./entrypoint.sh tokenizer -p in.txt -o out.txt` |
| `formatter` | Converts `.txt` to `.jsonl` via regex | `./entrypoint.sh formatter -p in.txt -o out.jsonl -d '\n\n\n'` |

`mt_alignment` is heuristic rather than semantic MT evaluation. It is designed to catch likely alignment problems such as shifted lines, number mismatches, URL/email mismatches, and structurally implausible source-target pairs. The command produces:

- an aligned source file
- an aligned target file
- mismatched source/target files
- a JSONL report with per-pair scores and reasons

---

## 🐋 With Docker

You can build a Docker image for the entire pipeline:
```bash
docker build -t proxectonos/nos:pipeline .
```

Run a command using the container:
```bash
docker run --mount src=$(pwd)/data,target=/data,type=bind proxectonos/nos:pipeline standard_pipeline /data/corpus.jsonl
```

---

## 📜 Citation

If you use this software in your research, please cite:

> Iria de-Dios-Flores, Silvia Paniagua Suárez, Cristina Carbajal Pérez, Daniel Bardanca Outeiriño, Marcos Garcia, and Pablo Gamallo. 2024. **CorpusNÓS: A massive Galician corpus for training large language models**. In *Proceedings of the 16th International Conference on Computational Processing of Portuguese - Vol. 1*, pages 593–599, Santiago de Compostela, Galicia/Spain. Association for Computational Linguistics.

## ⚖️ License
This project is licensed under the MIT License.
