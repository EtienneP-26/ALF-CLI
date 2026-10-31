from AlfTools import *

DEFAULT_MAX_TOKENS: int = 8192
MIN_MAX_TOKENS: int = 4096
ALERT_RATIO: float = 0.8
COMPACT_RATIO: float = 0.7

logoAlf: str = """
  /$$$$$$  /$$       /$$$$$$$$
 /$$__  $$| $$      | $$_____/
| $$  \\ $$| $$      | $$
| $$$$$$$$| $$      | $$$$$
| $$__  $$| $$      | $$__/
| $$  | $$| $$      | $$
| $$  | $$| $$$$$$$$| $$
|__/  |__/|________/|__/
"""

available = {
    "write_file": write_file,
    "read_file": read_file,
    "run_command": run_command,
    "web_search": web_search,
    "plan_task": plan_task,
}
tools = [write_file, read_file, run_command, web_search, plan_task]
