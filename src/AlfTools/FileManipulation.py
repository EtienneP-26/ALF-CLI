
__all__ = ["read_file", "write_file"]

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
