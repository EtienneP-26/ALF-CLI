import argparse
from Variables import DEFAULT_MAX_TOKENS, MIN_MAX_TOKENS

def maxTokensType(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid token budget `{value}`: expected an integer")
    if number < MIN_MAX_TOKENS:
        raise argparse.ArgumentTypeError(f"token budget must be at least {MIN_MAX_TOKENS}, got {number}")
    return number

def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="alf")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--continue", dest="continue_", action="store_true", help="reopen the last conversation")
    group.add_argument("--resume", metavar="ID_OR_NUMBER", help="reopen a conversation by id or by its number in `/conversations`")
    parser.add_argument("--max-tokens", dest="max_tokens", type=maxTokensType, default=None, metavar="N", help=f"context token budget sent to the model (num_ctx, default: the context length of the model, else {DEFAULT_MAX_TOKENS}, min {MIN_MAX_TOKENS})")
    parser.add_argument("--model", default="gemma4:e2b-mt", metavar="NAME", help="Ollama model to use (default: gemma4:e2b-mt)")
    parser.add_argument("--think",action="store_true", help="show the reasoning of the model (Thought / Action / Observation), if the model supports it")
    parser.add_argument("--auto", action="store_true", help="run commands and write files without asking")
    parser.add_argument("--allowed-dir", dest="allowed_dir", action="append", metavar="DIR", help="directory where read_file, write_file and run_command may go (repeatable, default: current directory)")
    parser.add_argument("--no-sandbox", dest="no_sandbox", action="store_true", help="run commands directly on this machine instead of in the docker sandbox (can cause security problems)")
    return parser.parse_args(argv)
