from subprocess import run, TimeoutExpired

def run_command(command: str) -> str:
    """Execute a command with a subprocess and return the result
    (timeout of 12 seconds)

    :param command: the command to execute
    :returns: the command: an line breaker and the result
    """
    try:
        r = run(command, shell=True, capture_output=True, text=True, timeout=12)
    except TimeoutExpired:
        return f"{command}:\ntimeout after 12s"
    return f"{command}:\nexit code {r.returncode}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
