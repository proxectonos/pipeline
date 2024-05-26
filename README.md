# NLP_processing for Galician
Pipeline developed to clean datasets used for training MT and LLM models.
## Installation

it is necessary to install git-lfs to clone the repository
``
sudo apt-get install git-lfs
``

## With docker
``
docker build -t proxectonos/nos:pipeline .
``
### How to process a file using the container

``
docker run --mount src=path/to/folder,target=/aliasfolderfordocker/,type=bind proxectonos/nos:pipeline command(tokenizer, detokenizer, etc) 
``

## Without Docker
#### install requirements.txt
``
pip install -r requirements.txt
``

#### make entrypoint executable
```
chmod +x entrypoint.sh
./entrypoint.sh command (see below)
```
### run standard text cleaning routine
By default it expects a .jsonl file. You can transform your .txt file into  .jsonl format by using the following command:
```
./entrypoint formatter -p $path_to_file -delimiter $regex_to_divide_txt -o $output_file_path
```
 Executing the command ./entrypoint standard_pipeline $path_input_file calls the following commands:
- encoding
- deduplication
- pyplexity (perplexity filter)
- quelingua (filter by lang)


## Available commands
``
sh entrypoint.sh  --help
``

- ``
sh entrypoint.sh  formatter --path --output  --technique --delimiter
``
Transforms a .txt file input into a .jsonl file. The --delimiter can be any  regex pattern, preceded by $ e.g. $'#\|\|\|#' where  #\|\|\|# is the pattern used to divide the text.
- ``
sh entrypoint.sh  tokenizer --path --output
``
tokenizes a latin script text. This tokenizer was developed mainly for Galician.
- ``
sh entrypoint.sh  detokenizer --path --output
``
detokenizes a text previously parsed with tokenizer.
- ``
sh entrypoint.sh  filter_lang --path --output --filter_results_by_lang
``
-line by line identification of the language a document is written in. If filter_results_by_lang is provided, the output file will only contain text in the specified language. filter_results_by_lang languages are 2 letter tags e.g. gl for Galician, es for Spanish, etc.
-``
sh entrypoint.sh  recoglang --path
``
Reads an input text file and returns the language it is written in.
- ``
sh entrypoint.sh  encoder --path --output
``
fixes encoding issues in files.
- ``
sh entrypoint.sh pyplexity
``
Calculates perplexity of the input. This script implements [PyPlexity](https://github.com/citiususc/pyplexity.git)

## How to cite this software
* Please, cite this paper if you use the modules of this NLP toolkit to clean a corpus:

Iria de-Dios-Flores, Silvia Paniagua Suárez, Cristina Carbajal Pérez, Daniel Bardanca Outeiriño, Marcos Garcia, and Pablo Gamallo. 2024. CorpusNÓS: A massive Galician corpus for training large language models. In Proceedings of the 16th International Conference on Computational Processing of Portuguese - Vol. 1, pages 593–599, Santiago de Compostela, Galicia/Spain. Association for Computational Lingustics.
