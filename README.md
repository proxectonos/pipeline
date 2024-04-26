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
##### install quelingua
```
cd methods/external
git clone https://github.com/gamallo/QueLingua quelingua_pipeline-main
```

#### make entrypoint executable
```
chmod +x entrypoint.sh
./entrypoint.sh command (see below)
```
### run standard text cleaning routine
By default it expects a .jsonl file. You can transform your .txt file into the expect .jsonl format by using the following command:
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
