def fix_doc(text: str) -> str:
    while "\n\n\n\n" in text:
        text = text.replace("\n\n\n\n", "\n\n\n")
    return text


def fix_newlines_doc(path: str):
    with open(path, "r", encoding="utf-8") as f:
        modified_text = fix_doc(text=f.read())

    with open(path, "w+", encoding="utf-8") as f:
        f.write(modified_text)
