import argparse

def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="alf")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--continue", dest="continue_", action="store_true", help="reopen the last conversation")
    group.add_argument("--resume", metavar="ID_OR_NUMBER", help="reopen a conversation by id or by its number in `/conversations`")
    return parser.parse_args(argv)
