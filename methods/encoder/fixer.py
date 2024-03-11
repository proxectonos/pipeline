# -*- coding: utf-8 -*-
import ftfy
import unicodedata
import emoji
import re
from methods.encoder.latin1_substitutions import LATIN1_ERROS
from methods.encoder.html_tags_substitutions import COMMON_HTML_TAGS, HTML_TAGS_UTF8, HTML_TAGS_WINDOWS, HTML_CONTROL_CHARS

# BSC filter for line breaks
def remove_newlines_filter(sentence, newline_symbols = ("\n", "\r")):
    """ Removes all new lines in sentences. CAREFUL: WE MIGHT LOSE POEMS AND POETRY USING THIS!!!
    """
    # CAREFUL: WE MIGHT LOSE POEMS AND POETRY USING THIS!!!
    #print(len(sentence))

    for newline_symbol in newline_symbols:
        sentence.replace(newline_symbol, '')
    return sentence

# BSC filter for remove initial and final blank spaces
def strip_filter(sentence):
    """Apply as last filter!"""
    return sentence.strip()


def encoding_fixer(text, filtered_categories:str, filtered_characters:str, remove_characters:str, emojies:bool):

    if type(text) == str:
        text = text.encode("utf-8", "ignore").decode("utf-8")
    else:
        text = text.decode("utf-8", "ignore")
    


    # Remove \x0 labels present as utf-8 characters
    # binari chars coded as strings "\x" need to scape the "\" for becoming binary again and decoded them again
    text = re.sub(r'\\x([0-9a-fA-F]{2})', lambda g: chr(int(g.group(1),16)), text)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda g: chr(int(g.group(1),16)), text)
    text = text.encode("utf-8", "ignore").decode("utf-8")

    
    # Remove latin-1 errors and html entities
    text = ftfy.fix_text(text)
    ## Remplázase un caracter de espazo inválido por outro válido (non son o mesmo!!)
    text = text.replace(' ', ' ')
    text = ''.join(char for char in text if char.isprintable()) ##elimina caracteres inválidos
    to_remov = [LATIN1_ERROS,  HTML_TAGS_UTF8, HTML_TAGS_WINDOWS, COMMON_HTML_TAGS, HTML_CONTROL_CHARS]
    for substitution_lst in to_remov:
        for char in substitution_lst.keys(): ## a completar!!
            text = re.sub(char, substitution_lst[char], text) ## Problemas com latin em utf-8: "Esta Ã© uma amostra de texto com caracteres binÃ¡ro"

    # Removing replacement characters
    text = re.sub(r'�|', ' ', text)
    
    emojies_filter = False
    if emojies:
            emojies_filter = True

    """ 
    Unicode categories : https://en.wikipedia.org/wiki/Template:General_Category_(Unicode)
    https://pypi.org/project/unicategories/
    Here the list of simbols in each category: https://www.fileformat.info/info/unicode/category/index.htm 
    """
    letters = ["Lu", "Ll", "Lt", "Lm", "Lo"]
    marks = ["Mn", "Mc", "Me"]
    numbers = ["Nd", "Nl", "No"]
    punctuation = ["Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"]
    symbols = ["Sm", "Sc", "Sk", "So"]
    separators = ["Zs", "Zl", "Zp"]
    others = ["Cc", "Cf", "Cs", "Co", "Cn"]

    cc_symbols = "␀␁␂␃␄␆␇␈␉␋␌␎␏␐␑␒␓␔␕␖␗␘␙␚␛␜␝␞␟␡␍␠"
    question_mark = "␅"
    new_line = "␤␊"

    if filtered_categories:
        final_categories=filtered_categories.split()
    else:
        final_categories = letters + marks + numbers + punctuation + separators + symbols + others 

    new_text = text

    for character in text:
        if character in cc_symbols:
            new_text = new_text.replace(character, ' ')
            character = ' '
        elif character == question_mark:
            new_text = new_text.replace(character, '?')
            character = '?'
        elif character in new_line:
            new_text = new_text.replace(character, '\n')
            character = "\n"
        u_category = unicodedata.category(character)

        if emojies_filter == True:
            if (u_category not in final_categories and character not in emoji.EMOJI_DATA and character not in filtered_characters) or character in remove_characters:
                new_text = new_text.replace(character, ' ')
        else:
            if (u_category not in final_categories and character not in filtered_characters) or character in remove_characters:
                new_text = new_text.replace(character, ' ')
    
    #Remove spaces and line breaks
    new_text = re.sub(r'([\s]+)', ' ', new_text)
    new_text = remove_newlines_filter(new_text)
    new_text = strip_filter(new_text)

    return new_text


