
__all__ = ["read_file", "write_file", "edit_file"]

import os

def read_file(file_path: str) -> str:
    """Read a given file with it's file path

    :param file_path: path to where the file is
    :returns: the file path: an line breaker and the file content
    """
    with open(file_path, 'r', encoding='utf-8') as f:
         content = f.read()
    return f"{file_path}:\n{content}"

def write_file(file_path: str, content: str) -> str:
    """Write in a given file thanks to it's file path and write the contentinside it
    (the write is an overwrite removing the old content of the file)

    :param file_path: path to where the file is
    :param content: the content to put inside
    :returns: return the number of char written
    """
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"wrote: {len(content)}"

def applyEdit(file_path: str, old_text: str, new_text: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    count = content.count(old_text) if old_text else 0
    if count != 1:
        raise ValueError(f"old_text found {count} times in {file_path}, expected exactly 1")
    return content.replace(old_text, new_text)

def edit_file(file_path: str, old_text: str, new_text: str) -> str:
    """Edit a file by replacing a piece of text, the rest of the file is kept

    :param file_path: path to where the file is
    :param old_text: the exact text to replace, it must appear exactly once in the file
    :param new_text: the text to put instead
    :returns: edited: and the file path
    """
    content = applyEdit(file_path, old_text, new_text)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"edited: {file_path}"
