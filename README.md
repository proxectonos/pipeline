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

Global options (available for all commands):

- `-m, --mode` (default: `jsonl`): Input/output format (`txt` or `jsonl`)
- `-w, --workers` (default: `6`): Number of worker processes for pipeline tasks
- `--eol`: Convert line endings to LF before processing
- `-lm, --list_methods`: Print methods from `subprocesses.py`

### `formatter`

- `-p, --path` (required): Input file path
- `-o, --output` (required): Output file path
- `-t, --technique` (default: `regex`)
- `-d, --delimiter` (default: `\n\n\n`)

Example:
```bash
./entrypoint.sh formatter -p in.txt -o out.jsonl -d '\n\n\n'
```

### `encoder`

- `-p, --path` (required): Input file
- `-o, --output` (required): Output file
- `-f, --field`: JSONL field to edit
- `-cat, --categories`: Categories for encoding fixer
- `-char, --characters`
- `-rmchar, --remove-characters`
- `-emo, --emojies` / `--no-emojies`

Example:
```bash
./entrypoint.sh encoder -p in.jsonl -o out.jsonl -m jsonl -f text
```

### `tokenizer`

- `-p, --path` (required)
- `-o, --output` (required)

Example:
```bash
./entrypoint.sh tokenizer -p in.txt -o out.txt -m txt
```

### `detokenizer`

- `-p, --path` (required)
- `-o, --output` (required)

Example:
```bash
./entrypoint.sh detokenizer -p in.txt -o out.txt -m txt
```

### `filter_lang`

- `-p, --path` (required): Input file
- `-o, --output` (required): Output file
- `-f, --filter_results_by_lang` (default: `False`)
- `-pf, --parallel_file`: Optional parallel file to filter in sync
- `-po, --parallel_output`: Output for filtered parallel file

Example:
```bash
./entrypoint.sh filter_lang -p in.jsonl -o out.jsonl -m jsonl -f gl
```

### `fasttext_gl`

- `-p, --path` (required): Input file
- `-o, --output` (required): Output file
- `-t, --threshold` (default: `0.05`)
- `-k, --top_k` (default: `3`)
- `-f, --field` (default: `text`)
- `-pf, --parallel_file`: Optional parallel file to filter in sync
- `-po, --parallel_output`: Output for filtered parallel file

Example:
```bash
./entrypoint.sh fasttext_gl -p in.jsonl -o out.jsonl -m jsonl -f text
```

### `pyplexity`

- `-p, --path` (required): Input file
- `-o, --output` (required): Output file
- `-pm, --path_model` (default: `models/bigrams_modelo-gl-bigramas-merged.st`)
- `-s, --score` / `--no-score` (default: enabled)
- `-f, --field`: JSONL field
- `-pl, --perpl_limit` (default: `2000`)
- `-r, --remove_low_scores` / `--no-remove_low_scores` (default: enabled)
- `-pf, --parallel_file`: Optional parallel file to filter in sync
- `-po, --parallel_output`: Output for filtered parallel file

Example:
```bash
./entrypoint.sh pyplexity -p in.jsonl -o out.jsonl -m jsonl -f text
```

### `normalize`

- `-p, --path` (required): Input file
- `-o, --output` (required): Output file
- `--detokenize` / `--no-detokenize` (default: `--no-detokenize`)
- `--jsonl_field`: Field for JSONL mode
- `-b, --bel` / `--no-bel`
- `-e, --exact` / `--no-exact`

Example:
```bash
./entrypoint.sh normalize -p in.txt -o out.txt -m txt --no-detokenize
```

### `deduplication`

- `-p, --path` (required)
- `-o, --output`
- `-f, --field`: JSONL field
- `--type` (`simple` or `jaccard`, default: `simple`)
- `-ilf, --input_lf` (default: `3`)
- `-olf, --output_lf` (default: `2`)
- `-t, --threshold` (default: `15`)
- `-s, --save_duplicates` / `--no-save_duplicates`

Example:
```bash
./entrypoint.sh deduplication -p in.jsonl -o out.jsonl --type simple -m jsonl
```

### `jaccard`

- `-p, --path` (required)
- `-o, --output_file` (store results to file)
- `-md, --max_documents`
- `-lt, --length_threshold` (default: `3`)
- `-lsh, --lsh_threshold` (default: `0.8`)
- `-gds, --generate_deduplication_samples`

Example:
```bash
./entrypoint.sh jaccard -p in.jsonl -m jsonl -o
```

### `mt_deduplication`

- `-s, --source` (required)
- `-t, --target` (required)
- `-f, --field`: Required for JSONL alignment keys
- `-d, --save_duplicates` / `--no-save_duplicates`

Example:
```bash
./entrypoint.sh mt_deduplication -s src.jsonl -t tgt.jsonl -m jsonl -f text
```

### `mt_alignment`

- `-s, --source` (required)
- `-t, --target` (required)
- `-f, --field`: JSONL text field
- `-ot, --output_tag` (default: `_alignment`)
- `-rp, --report_path`: Optional report output path
- `-sl, --source_lang` (default: `glg_Latn`)
- `-tl, --target_lang` (default: `eng_Latn`)
- `-sc, --scorer` (choices: `blaser_qe`, `cosine`, default: `blaser_qe`)
- `-d, --device` (default: `cuda`)
- `-bs, --batch_size` (default: `256`)
- `-bmt, --batch_max_tokens` (default: `None`)
- `-st, --score_threshold` (default: `3.0`)
- `-sm, --shift_margin` (default: `0.10`)
- `-nw, --neighbor_window` (default: `2`)
- `-mlr, --min_length_ratio` (default: `0.30`)

`mt_alignment` uses SONAR embeddings and supports two scoring modes:

- `blaser_qe` (default): BLASER 2.0 Quality Estimation score 
- `cosine`: cosine similarity over SONAR embeddings

Threshold guidance:

- For `blaser_qe`, start around `-st 3.0`
- For `cosine`, start around `-st 0.65`

Outputs:

- aligned source file
- aligned target file
- mismatched source file
- mismatched target file
- JSONL report with per-pair scores and reasons

Example:
```bash
./entrypoint.sh mt_alignment -s src.txt -t tgt.txt -m txt -sl glg_Latn -tl eng_Latn -sc blaser_qe -st 3.0 -d cuda
```

Full command with all options:
```bash
./entrypoint.sh mt_alignment \
  -s src.txt \
  -t tgt.txt \
  -m txt \
  -f text \
  -ot _alignment \
  -rp alignment_report.jsonl \
  -sl glg_Latn \
  -tl eng_Latn \
  -sc blaser_qe \
  -d cuda \
  -bs 256 \
  -bmt 8192 \
  -st 3.0 \
  -sm 0.10 \
  -nw 2 \
  -mlr 0.30
```

Language code reference:

- SONAR model card (includes supported language codes and examples): https://huggingface.co/facebook/SONAR/blob/main/README.md

Troubleshooting (Conda + BLASER):

If you see this error:

`OSError: fairseq2 requires libsndfile`

install the missing dependency in your conda environment:

```bash
conda install -n pipeline2 -c conda-forge libsndfile==1.0.31
```

### `mt_quelingua`

- `-s, --source` (required)
- `-t, --target` (required)
- `-cl, --correct_lang_source` (required)
- `-ot, --output_tag` (default: `_quelingua`)
- `-fm, --filter_method` (`quelingua` or `fasttext`, default: `quelingua`)
- `-f, --field`: JSONL field
- `-th, --threshold` (default: `0.4`)
- `-tk, --top_k` (default: `3`)

Example:
```bash
./entrypoint.sh mt_quelingua -s src.txt -t tgt.txt -cl gl -m txt
```

### `mt_transliteration`

- `-p, --path` (required)
- `-o, --output` (required)
- `-q, --quelingua` / `--no-quelingua` (default: disabled)
- `-f, --field`: JSONL field

Example:
```bash
./entrypoint.sh mt_transliteration -p src.txt -o out.txt -m txt
```

### `recoglang`

- `-p, --path` (required)

Example:
```bash
./entrypoint.sh recoglang -p in.txt
```

### `fix_new_lines`

- `-p, --path` (required)

Example:
```bash
./entrypoint.sh fix_new_lines -p in.txt
```

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
