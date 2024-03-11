# Eliminação de duplicadas

## Corpus em formato saltos de linha

### Corpus separado em vários ficheiros

```
$ python3 deduplicate_parts.py \
-f newlines \
-i 2 \
bne_clean_preproc_encoding_pypl_quelingua_final_revisado/corpus_bne_part* \
-O bne_clean_preproc_encoding_pypl_quelingua_final_revisado_dedupl
(...)
5363542 documents processed in total, 1588374 unique
```

### Corpus num só ficheiro

```
$ ls -1 corpus_bne_part* | while read f
do
    cat $f >> ../concat_bne.txt
    echo >> ../concat_bne.txt
    echo >> ../concat_bne.txt
done

$ python3 deduplicate.py -f newlines -i 2 concat_bne.txt > concat_bne_dedupl.txt 
5363542 documents processed, 1588374 unique
```

# Ficheiros

- `corpus_documents.py`, `tests`: classe para trabalhar com documentos em formato JSONL ou *newlines* e os tests unitários.
- `count.py`: script para contar documentos num ou vários ficheiros de um corpus em formato *newlines*. Com `-i NUM` é possível estabelecer o número de *newlines* do separador de documento.
- `deduplicate_parts.py`: elimina duplicados de 1 ou máis ficheiros e guarda o resultado conservando a estrutura original do corpus
- `deduplicate.py`: elimina duplicados de 1 ficheiro e escreve o resultado a stdout.
