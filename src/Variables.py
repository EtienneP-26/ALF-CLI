from AlfTools import *

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

listCommands: list[str] = ["/exit", "/model"] # /help /clear etc.
available = {
    "write_file": write_file,
    "read_file": read_file,
    "run_command": run_command,
    "web_search": web_search,
}
tools = [write_file, read_file, run_command, web_search]
