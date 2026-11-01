
__all__ = ["read_file", "write_file", "edit_file", "list_dir"]

import os

MAX_READ_SIZE = 1_000_000

def read_file(file_path: str) -> str:
    """Read a given text file with it's file path.
    Files over 1 MB and binary files are refused.

    :param file_path: path to where the file is
    :returns: the file path: an line breaker and the file content
    """
    size = os.path.getsize(file_path)
    if size > MAX_READ_SIZE:
        raise ValueError(f"{file_path} is too large to read: {size} bytes (limit {MAX_READ_SIZE})")
    with open(file_path, 'rb') as f:
        data = f.read()
    try:
        if b"\0" in data:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "NUL byte")
        content = data.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError(f"{file_path} is a binary file, it cannot be read as text") from None
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

def list_dir(path: str = ".") -> str:
    """List the entries of a directory (one level, .git hidden), folders end with /

    :param path: path to the directory, the current directory by default
    :returns: one entry per line sorted by name, at most 200 entries
    """
    names = sorted(n for n in os.listdir(path) if n != ".git")
    lines = [n + "/" if os.path.isdir(os.path.join(path, n)) else n for n in names[:200]]
    if len(names) > 200:
        lines.append(f"[truncated: {len(names) - 200} more entries]")
    return "\n".join(lines)
