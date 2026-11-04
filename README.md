<p align="center"><img src="assets/logo.png" width="200"></p>

<h1 align="center">ALF-CLI</h1>

<p align="center"><em>A local, private command-line development agent, powered by Ollama.</em></p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-personal%20use-red">
  <img alt="Ollama" src="https://img.shields.io/badge/Ollama-local-black?logo=ollama&logoColor=white">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-compatible-1800f7">
</p>

## Table of contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [Configuration](#configuration)
- [Security](#security)
- [Architecture](#architecture)
- [Tests](#tests)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

## Features

ALF-CLI (command `alf`) is a conversational agent that runs in your terminal and uses a model served by [Ollama](https://ollama.com). The model can call tools to act on your project:

| Tool | Role |
| --- | --- |
| `read_file` | read a file |
| `write_file` | create or overwrite a file (diff shown) |
| `edit_file` | replace a piece of text in a file |
| `list_dir` | list a directory |
| `run_command` | run a command in an isolated Docker container |
| `web_search` | web search via DuckDuckGo |
| `plan_task` | announce a plan in steps |

Also:

- streamed responses rendered as Markdown (rich);
- optional display of the model's reasoning (`--think`);
- saved, resumable and renamable conversations;
- context window tracking, with a warning and automatic compaction by summarizing older messages;
- MCP servers (Claude Desktop format) whose tools are added to the agent;
- `ask` mode (confirmation before each sensitive action) or `auto`.

## Prerequisites

- Python 3.10 or newer
- [Ollama](https://ollama.com) installed and running, with at least one model downloaded (default `gemma4:e2b-mt`)
- [Docker](https://www.docker.com) for the `run_command` sandbox (otherwise use `--no-sandbox`)
- `uvx` (`uv` tool) if you keep the `time` MCP server from `mcp_servers.json`

## Installation

```bash
git clone <repository-url> ALF-CLI
cd ALF-CLI
pip install -r requirements.txt

# sandbox image used by run_command
docker build -t alf-sandbox .

# default model
ollama pull gemma4:e2b-mt

# (optional) make the `alf` command available everywhere
sudo ln -s "$PWD/bin/alf" /usr/local/bin/alf
```

The launcher `bin/alf` runs `src/alf` wherever it is called from.

## Usage

```bash
alf                                   # new conversation in the current folder
alf --model qwen3:8b --think          # another model, with reasoning shown
alf --continue                        # reopen the last conversation
alf --resume 2                        # reopen conversation no. 2 in /conversations
alf --allowed-dir ~/projet --allowed-dir ~/notes
alf --auto                            # do not ask before acting
alf --no-sandbox                      # commands run directly on the machine (risky)
alf --mcp-config ./mcp_servers.json   # use a specific MCP file
```

Options of `alf --help`:

| Option | Description |
| --- | --- |
| `--continue` | reopen the last conversation |
| `--resume ID_OR_NUMBER` | reopen a conversation by id or by its number in `/conversations` |
| `--max-tokens N` | context budget sent to the model (`num_ctx`), minimum 4096; by default the model's context length, otherwise 8192 |
| `--model NAME` | Ollama model (default: `gemma4:e2b-mt`) |
| `--think` | show the model's reasoning, if it supports it |
| `--auto` | run commands and write files without asking |
| `--allowed-dir DIR` | folder accessible to the tools (repeatable, default: current folder) |
| `--no-sandbox` | run commands without Docker |
| `--mcp-config FILE` | MCP configuration, replaces `$ALF_HOME/mcp_servers.json` |

`--continue` and `--resume` are mutually exclusive.

## Commands

Type them at the `alf` prompt:

| Command | Effect |
| --- | --- |
| `/help` | list the commands |
| `/exit` | quit |
| `/model [name]` | choose a model (menu when no argument is given) |
| `/mode [ask\|auto]` | choose the confirmation mode |
| `/think [on\|off\|show]` | turn on reasoning, or show the last one |
| `/new` | start a new conversation |
| `/rename <title>` | rename the current conversation |
| `/conversations` | list saved conversations, most recent first |
| `/resume <number>` | resume a conversation |
| `/delete <number>` | delete a conversation (with confirmation) |

## Configuration

### Environment variables

| Variable | Role | Default |
| --- | --- | --- |
| `ALF_HOME` | data folder (conversations, `mcp_servers.json`) | `~/.alf` |
| `OLLAMA_HOST` | address of the Ollama server | `http://localhost:11434` |

Conversations are stored as JSON in `$ALF_HOME/conversations/`.

### MCP servers

ALF-CLI reads `$ALF_HOME/mcp_servers.json` (or the file given by `--mcp-config`) in Claude Desktop format. The tools of each server are exposed to the model under the name `<server>__<tool>`. An invalid or failing server is reported and skipped, without blocking startup.

Example provided in `mcp_servers.json`:

```json
{
  "mcpServers": {
    "devtools": {"command": "python3", "args": ["src/McpServers/DevTools.py"]},
    "time": {"command": "uvx", "args": ["mcp-server-time"]}
  }
}
```

`devtools` is a small server in the repository whose `find_todos` tool lists the TODO and FIXME comments in the current folder.

## Security

- **Allowed folders**: the file tools and `run_command` do not go outside the folders given by `--allowed-dir` (current folder by default).
- **Secret files** (`.env`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, etc.): access denied.
- **Sandbox**: `run_command` starts a disposable `alf-sandbox` container with no network, a read-only file system, 512 MB of memory, 1 CPU, at most 100 processes, all capabilities dropped, `.git` read-only, secrets hidden, and a 12 s timeout. If the image or Docker is missing, the command is refused.
- **`ask` mode**: confirmation is requested before acting; `--auto` or `/mode auto` turns it off.

## Architecture

```text
.
├── bin/alf                 # launcher
├── src/
│   ├── alf                 # entry point and main loop
│   ├── Variables.py        # logo, available tools, context constants
│   ├── Context.py          # context usage estimation and display
│   ├── Memory.py           # saving conversations (ALF_HOME)
│   ├── HandleResponse.py   # handling responses and tool calls
│   ├── AlfTools/           # read/write/edit, run_command, web_search, plan_task,
│   │                       # permissions, MCP client
│   ├── CliTools/           # arguments and display (rich, prompt_toolkit)
│   ├── Commands/           # slash commands (/help, /model, ...)
│   ├── OllamaTools/        # connection, streaming, models, context summary
│   └── McpServers/         # example MCP server (devtools)
├── tests/                  # pytest tests
├── docs/                   # documentation
├── assets/logo.png
├── mcp_servers.json        # example MCP configuration
├── Dockerfile              # alf-sandbox image
└── docker-compose.yml
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

## Contributing

Contributions go through a validated issue, then a branch created from `dev`. The full rules are in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Personal use only, all rights reserved. See the [LICENCE](LICENCE) file.

## Author

Etienne Pouille — [GitHub: EtienneP-26](https://github.com/EtienneP-26)
