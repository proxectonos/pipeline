import re

##falta importar ftfy para usar função 'fix'

def encoding_fixer_2(text):
    #cleaned_text = re.sub(r'[^\x00-\x7F]', '', text) ##Isto elimina demasiado...
    
    text = text.encode('utf-8', 'ignore').decode('utf-8') ##elimina binários \x1F, x00, etc...
    text = re.sub(r'[\x01-\x1F\x7F-\x9F]', '', text) ## rango que elimina caracteres de controlo: tab, carriage return, etc. Hai que verificar se é um subconjunto dos caracteres FALSE que devolve a função isprintable()
    text = ''.join(char for char in text if char.isprintable()) ##elimina caracteres inválidos
   # text = re.sub(r'[U+D800-U+DFFF]', '', text) 
    text = re.sub(r'[\uFFFD\uFFFE\uFFFF\uFEFF\uFFFC]', '', text) ##elimina o resto de caracteres estranhos mais frequentes que imos encontrando: e.g. � ou ￼
    
    #text = text.encode('latin-1', 'ignore').decode('utf-8')
    to_remov = {"Ã¡": "á", "Ã©": "é", "Ã ": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ", "Ã§": "ç", "Ã£": "ã", "Ãµ": "õ", "áº½": "ẽ", "Ã<81>": "Á", "Ã<89>": "É"} ## a completar!!
    for char in to_remov.keys():
        text = re.sub(char, to_remov[char], text) ## Problemas com latin em utf-8: "Esta Ã© uma amostra de texto com caracteres binÃ¡ro"
    return text

# Exemplo de input com diferentes tipos de problemas de encoding:
#input = "Esta é uma amostra de texto com caracteres binários: \x00 e especiais: \x1F. Aqui misturo cousas que hai que eliminar e outras (signos, alfabetos e emojis) que não: +*{ºª  ￼ � � � 这是一段中文文本ة هذا هو نص باللغة العربية. -- 🙂 \uFFFF , 𓀀,  © and ™ . E agora problemas com Latin: Esta Ã© uma amostra de texto com caracteres binÃ¡ros, sÃ³s cÃºs, riquiÃ±o e preÃ§o, vÃ£o, Ãµes, áº½les, Ã<89>s. Ã<89> meu. dÃ a tÃ a "
#input =  sys.argv[1]
#output = limpar_texto(input)
#print(output)
