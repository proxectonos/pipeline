# NLP_processing

corpus novo para GPT:

-- encoding
-- pyplexity
-- quelingua (filter by lang)
-- scrips de processamento_crawler no github.

final files /home/compartido/nos/INPUT/FORMATADO/TEXTO/textos_gpt

--
## INSTALLATION WITH DOCKER
- como criar imagem
- adicionar exemplos para cada passo da pipeline

``
docker build -t proxectonos/nos:pipeline .
``
### docker run --mount src=path/to/folder,target=/aliasfolderfordocker/,type=bind proxectonos/nos:pipeline command(tokenizer, detokenizer, etc) 

## USAGE WITHOUT DOCKER

``
python3 main.py --help
``

``
python3 main.py tokenizer --path --output
``

``
python3 main.py detokenizer --path --output
``

``
python3 main.py filter_lang --path --output
``

``
python3 main.py recoglang --path
``

``
python3 main.py encoder --path --output
``

``
sh entrypoint.sh pyplexity
``
