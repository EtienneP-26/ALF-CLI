import os
from subprocess import run, TimeoutExpired
from uuid import uuid4

from AlfTools.Permissions import ALLOWED_DIRS, check_path

SANDBOX = True

def run_command(command: str) -> str:
    """Execute a command in an isolated container and return the result
    (no network, only the allowed directories visible, .git read-only,
    timeout of 12 seconds)

    :param command: the command to execute
    :returns: the command: an line breaker and the result
    """
    if not SANDBOX:
        try:
            r = run(command, shell=True, capture_output=True, text=True, timeout=12)
        except TimeoutExpired:
            return f"{command}:\ntimeout after 12s"
        return f"{command}:\nexit code {r.returncode}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    try:
        check = run(["docker", "image", "inspect", "alf-sandbox"], capture_output=True, text=True, timeout=5)
        details = check.stderr.strip() if check.returncode else ""
    except (FileNotFoundError, TimeoutExpired) as e:
        check, details = None, repr(e)
    if check is None or check.returncode:
        return (f"{command}:\nrefused: sandbox unavailable, nothing was run\n{details}\n"
                "hint: if docker is missing, build the image with `docker build -t alf-sandbox .`, "
                "run ALF-CLI on the host and not inside a container, or use `--no-sandbox`")
    try:
        workdir = check_path(os.getcwd())
    except PermissionError:
        workdir = os.path.realpath(ALLOWED_DIRS[0])
    name = f"alf-{uuid4().hex}"
    argv = ["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only", "--tmpfs", "/tmp",
            "--memory", "512m", "--cpus", "1", "--pids-limit", "100", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
    dirs = [os.path.realpath(d) for d in ALLOWED_DIRS]
    for d in dirs:
        argv += ["-v", f"{d}:{d}"]
    for d in dirs:
        if os.path.isdir(os.path.join(d, ".git")):
            argv += ["-v", f"{d}/.git:{d}/.git:ro"]
    argv += ["-w", workdir, "alf-sandbox", "timeout", "-s", "KILL", "13", "sh", "-c", command]
    try:
        r = run(argv, capture_output=True, text=True, timeout=12)
    except TimeoutExpired:
        try:
            run(["docker", "kill", name], capture_output=True, timeout=5)
        except (OSError, TimeoutExpired):
            pass
        return f"{command}:\ntimeout after 12s"
    return f"{command}:\nexit code {r.returncode}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
