import fnmatch
import os
import shlex

ALLOWED_DIRS: list[str] = [os.getcwd()]

SECRET_PATTERNS = [".env", ".env.*", "*.pem", "*.key", "id_rsa*", "id_ed25519*", "credentials*", "secrets*", "*.secret"]

def isSecret(file_path: str) -> bool:
    name = os.path.basename(os.path.realpath(file_path)).lower()
    return name != ".env.example" and any(fnmatch.fnmatch(name, p) for p in SECRET_PATTERNS)

def check_path(file_path: str) -> str:
    try:
        real = os.path.realpath(file_path)
        for allowed in ALLOWED_DIRS:
            base = os.path.realpath(allowed)
            if os.path.commonpath([real, base]) == base:
                return real
    except (ValueError, TypeError):
        pass
    raise PermissionError(f"Access denied: {str(file_path)[:200]!a} is outside the allowed directories")

def check_command(command: str) -> None:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError as e:
        raise PermissionError(f"Access denied: cannot parse the command ({e})")
    for token in tokens:
        if "=" in token:
            token = token.split("=", 1)[1]
        if "://" in token or token == "/dev/null":
            continue
        token = os.path.expanduser(os.path.expandvars(token))
        if isSecret(token):
            raise PermissionError(f"Access denied: {token[:200]!a} is a secret file")
        if "/" in token or token.startswith("~") or token == "..":
            check_path(token)

def checkAccess(name: str, args: dict) -> None:
    key = {"read_file": "file_path", "write_file": "file_path", "edit_file": "file_path", "list_dir": "path", "run_command": "command"}.get(name)
    if key is None:
        return
    value = args.get(key, "." if name == "list_dir" else None)
    if not isinstance(value, str):
        raise PermissionError(f"Access denied: `{key}` must be a string")
    if key == "command":
        return check_command(value)
    real = check_path(value)
    if name in ("read_file", "edit_file") and isSecret(real):
        raise PermissionError(f"Access denied: {value[:200]!a} is a secret file")
    if name in ("write_file", "edit_file") and ".git" in real.split(os.sep):
        raise PermissionError(f"Access denied: {value[:200]!a} is inside .git")
