# NLP_processing

corpus novo para GPT:

- encoding
- pyplexity
- quelingua (filter by lang)
- scrips de processamento_crawler no github.


final files /home/compartido/nos/INPUT/FORMATADO/TEXTO/textos_gpt

## INSTALLATION WITH DOCKER
- como criar imagem
- adicionar exemplos para cada passo da pipeline

``
docker build -t proxectonos/nos:pipeline .
``
### docker run --mount src=path/to/folder,target=/aliasfolderfordocker/,type=bind proxectonos/nos:pipeline command(tokenizer, detokenizer, etc) 

## USAGE WITHOUT DOCKER

### run standard text cleaning routine

``
sh entrypoint.sh  standard_pipeline 
$path_file  
``


``
sh entrypoint.sh  --help
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
