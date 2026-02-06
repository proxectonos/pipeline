FROM ubuntu:22.04
ENV TZ=Europe/Madrid

ARG DEBIAN_FRONTEND=noninteractive
COPY . /pipeline/

WORKDIR /pipeline
RUN \
  apt-get update && \
  apt-get -y upgrade \
  && apt-get install python3-pip -y \
  && apt-get install -y git \
  && apt-get install -y dos2unix

WORKDIR /pipeline/methods/external

RUN [ -d pyplexity ] && [ "$(ls -A pyplexity 2>/dev/null)" ] || \
    git clone https://github.com/citiususc/pyplexity.git

RUN [ -d port2gal ] && [ "$(ls -A port2gal 2>/dev/null)" ] || \
    git clone https://github.com/gamallo/port2gal.git

RUN [ -d quelingua_pipeline-main ] && [ "$(ls -A quelingua_pipeline-main 2>/dev/null)" ] || \
    git clone https://github.com/gamallo/QueLingua quelingua_pipeline-main
    
RUN chmod -R 777 quelingua_pipeline-main

WORKDIR /pipeline/methods/external/pyplexity

RUN pip install -r requirements.txt
#RUN pip install .
RUN python3 setup.py install

WORKDIR /pipeline
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "entrypoint.sh"]
