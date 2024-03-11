"""
List of encoding problems related to latin-1 characteres that ftfy do not fix.
Example of debugging list: 
https://www.i18nqa.com/debug/utf8-debug.html
I can fix characters with more than 1-char equivalence (e.g. substitute "Ã…" with "Å" but in de case of "Á" and	"Ã" is imposible without context)
"""
LATIN1_ERROS = {
    "Ã¡": "á",
    "Ã©": "é",
    "Ã ": "í",
    "Ã³": "ó",
    "Ãº": "ú",
    "Ã±": "ñ",
    "Ã§": "ç",
    "Ã£": "ã",
    "Ãµ": "õ",
    "áº½": "ẽ",
    "Ã<81>": "Á",
    "Ã<89>": "É",
    "Æ'": "ƒ",
    "Å'": "Œ",
    "Ëœ": "˜",
    "â\"¢": "™",
    "Å¡": "š",
    "Å\"": "œ",
    "Â¥": "¥",
    "Ã…": "Å",
    "ÃŒ": "Ì",
    "ÃŽ": "Î",
    "Ã'": "Ò",
    "Ãœ": "Ü",
    "Ã¥": "å"
    
}