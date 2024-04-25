# NLP_processing
Pipeline developed to clean datasets used for training MT and LLM models.
## Installation

``
docker build -t proxectonos/nos:pipeline .
``
### How to process a file using the container

``
docker run --mount src=path/to/folder,target=/aliasfolderfordocker/,type=bind proxectonos/nos:pipeline command(tokenizer, detokenizer, etc) 
``

## Without Docker
install requirements.txt
    pip install -r requirements.txt
    
install quelingua
cd methods/external
git clone https://github.com/gamallo/QueLingua quelingua_pipeline-main

``
chmod +x entrypoint.sh
./entrypoint.sh command (see below)
``
### run standard text cleaning routine
This command executes the following commands:
- encoding
- deduplication
- pyplexity (perplexity filter)
- quelingua (filter by lang)
  
``
chmod +x entrypoint.sh
./entrypoint.sh  standard_pipeline  $path_file  
``

## Available commands
``
sh entrypoint.sh  --help
``

``
sh entrypoint.sh  formatter --path --output  --technique --delimiter
``

``
sh entrypoint.sh  tokenizer --path --output
``

``
sh entrypoint.sh  detokenizer --path --output
``

``
sh entrypoint.sh  filter_lang --path --output
``

``
sh entrypoint.sh  recoglang --path
``

``
sh entrypoint.sh  encoder --path --output
``

``
sh entrypoint.sh pyplexity
``
