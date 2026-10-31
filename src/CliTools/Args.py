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
    parser.add_argument("--max-tokens", dest="max_tokens", type=maxTokensType, default=DEFAULT_MAX_TOKENS, metavar="N", help=f"context token budget sent to the model (num_ctx, default {DEFAULT_MAX_TOKENS}, min {MIN_MAX_TOKENS})")
    return parser.parse_args(argv)
