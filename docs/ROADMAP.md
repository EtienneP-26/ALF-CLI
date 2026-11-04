# ALF-CLI: roadmap

## Goal

ALF-CLI today only works with a local Ollama and with models that support tools. This roadmap plans three things. First, it must be possible to talk to any model, even one without tools. Next, it must be possible to target a remote server or another engine: llama.cpp, vLLM, LM Studio, or an OpenAI-compatible API. Finally, the project must become easier to install and more robust, without breaking what already works.

Effort: **S** < 1 day, **M** 1 to 3 days, **L** more than 3 days.

---

## 1. Models without tools (e.g. `gemma2:2b`)

**Finding.** `getResponse` always sends `tools=` (`src/OllamaTools/ResponseHandle.py:226-233`). Ollama then replies `ResponseError "... does not support tools"`. The error is caught at `src/alf:111`, and the history is then rolled back. Result: you cannot talk to this model at all.

### 1a. Detection and fallback to simple chat (S)
- **What.**
  - Add `supportsTools(client, model)` in `src/OllamaTools/ModelContext.py`. This function reads `"tools" in client.show(model).capabilities`, following the pattern of `supportsThinking`.
  - Add a `toolMode` field to `State` (`src/Commands/registry.py`). Compute it at startup (`src/alf`) and on each `/model` (`src/Commands/builtin.py:108-126`).
  - Safety fallback: in `getResponse`, if a `ResponseError` with "does not support tools" is received, retry once with `tools=[]` and report it only once.
  - Provide a second system prompt without the "Tools" section and without the agent loop. Today, `SystemPrompt` names the tools hard-coded (`ResponseHandle.py:188`).
- **Why.** Using `capabilities` avoids a round trip through an error. The fallback covers older Ollama versions and other engines.
- **Limits.** In this mode, the model can no longer act on the project. The user must be told, for example with "chat mode: tools disabled".

### 1b. Tools via prompt, as JSON in the text (M)
- **What.**
  - New option `--tool-mode auto|native|prompt|off`.
  - In `prompt` mode, the system prompt describes each tool with its JSON schema. It is generated from the `tools`: Python functions and MCP `ollama.Tool` objects.
  - The model is asked to answer with a block ` ```tool {"name": ..., "arguments": {...}}``` `.
  - New module `src/OllamaTools/PromptTools.py`. It parses the text after `collectStream` and builds `Message.ToolCall` objects. So, **the loop in `HandleResponse.py` stays the same**.
  - When sending back to the model, `tool` messages become `user` messages "Observation (read_file): …". Indeed, the templates of models without tools ignore the `tool` role.
  - In `thinkVisual` (`src/CliTools/Cli.py:191`), hide the display from ` ```tool `.
- **Limits.** Small models (2B) often produce invalid JSON. A retry with the parse error is needed, at most once. Reliability will stay well below native tools.
- **Dependencies.** None.

---

## 2. Remote machines

### 2a. Remote model (S)
- **What.** Today, only `OLLAMA_HOST` is read (`src/OllamaTools/ConnectionOllama.py:4`). We add:
  - the options `--host URL`, `--ca-cert FILE`, `--timeout S`;
  - an API key read from the `ALF_API_KEY` environment variable, sent as an `Authorization: Bearer` header;
  - TLS through a `https://` URL.

  `ollama.Client(host, headers=..., timeout=httpx.Timeout(connect=5, read=300), verify=ca)` already passes these settings to httpx. The client must be created in a factory called after `parseArgs`, instead of at import time.
- **SSH tunnel.**
  - Document `ssh -N -L 11434:localhost:11434 user@gpu`. Ollama has no authentication: never expose it on `0.0.0.0`.
  - Optionally, `--ssh-tunnel user@host` starts this tunnel with `subprocess` and closes it on exit. Effort S.
- **Security impact.**
  - The content of read files, command outputs and the history travel over the network. The README's "local and private" promise no longer holds.
  - A warning at startup is needed if the host is not on the loopback interface.
  - No `--api-key` command-line option: the key would be visible in `ps` and in the shell history.

### 2b. Remote execution (L, experimental)
- **What.** Run `run_command` and the file tools on a remote machine over SSH, with a `--exec-host` option.
- **Where.** The following must be changed:
  - `AlfTools/RunCommand.py`: `ssh host -- docker run ...`;
  - `AlfTools/FileManipulation.py`;
  - `AlfTools/Permissions.py`. `check_path` uses `os.path.realpath` locally and must perform this check on the remote side.
- **Limits and risks.**
  - The sandbox and the secret rules must be redone remotely, and SSH host key verification must be strict.
  - The SSH agent must not be forwarded.
  - A leak of paths between the local and the remote machine is possible.
  - `paramiko` would be a new dependency. The `ssh` binary is enough.
- **Recommended alternative.** Install `alf` on the remote machine (see point 4, pipx) and connect to it over SSH. The cost is zero and the security model stays the same.

---

## 3. Other engines and the "provider" abstraction

- **What.** New package `src/Providers/` containing:
  - `base.py`: the `Provider` interface with `chat(messages, tools, think, stream, on_text, on_thinking) -> ChatResponse`, `list_models()`, `capabilities(model)`, `context_length(model)` and `unload(model)` (optional);
  - `ollama.py`, which takes over the current code;
  - `openai_compat.py` for `/v1/chat/completions`. It covers llama.cpp (`--jinja`), vLLM (`--enable-auto-tool-choice --tool-call-parser`), LM Studio and cloud APIs.
- **Normalized format.** We keep the `ollama.Message` / `ChatResponse` types as the internal format. So `HandleResponse.py`, `Memory._serialize` and `Context.py` do not change.

| Point | Ollama | OpenAI-compatible |
|---|---|---|
| Tool call arguments | `dict` | JSON string, `id` required |
| Tool result | `tool_name` | `tool_call_id` (to generate and keep) |
| Streaming | complete tool calls per chunk | SSE deltas, to be assembled by `index` |
| Reasoning | `message.thinking`, `think=` | `reasoning_content` (vLLM, llama.cpp) or `<think>` tags in the text |
| Tokens | `prompt_eval_count` / `eval_count` | `usage` (`stream_options.include_usage`) |
| Context | `options.num_ctx` | set by the server (`/props` for llama.cpp, `max_model_len` for vLLM) |
| Capabilities | `/api/show` | no standard: assume tools are available, with fallback 1a |

- **Files to change.**
  - `ConnectionOllama.py`, to be replaced by a factory;
  - `ResponseHandle.py`;
  - `Summarize.py:51`;
  - `ModelContext.py`;
  - `HandleResponse.py:9-18` for the token count;
  - `builtin.py` for `/model`;
  - `src/alf`: `ollama.ResponseError` exceptions to be replaced by `ProviderError`, and `keep_alive=0` (line 131) to be replaced by `unload()`.
- **Migration.**
  1. Create `OllamaProvider` by moving the code, without changing behavior. Existing tests must pass.
  2. Add `--provider ollama|openai` and `--base-url`.
  3. Add the OpenAI-compatible provider, with tests on recorded SSE responses.
- **Choice: httpx (already present via ollama) rather than the `openai` SDK.**
  - What it brings: no new dependency.
  - Limit: a small SSE parser (about 60 lines) must be written, and retries must be handled by hand.
  - The `openai` SDK would be more robust, but it is one more dependency. Your choice.
- **Effort.** L.

---

## 4. Other improvements

| Topic | What | Where | Effort |
| --- | --- | --- | --- |
| Config file | `~/.alf/config.toml` with profiles (`provider`, `url`, `model`, `api_key_env`, `tool_mode`). Priority: option > env var > profile > default. `/profile <name>` command. | `CliTools/Args.py`, new `Config.py` | M |
| Non-interactive mode | `alf -p "..."` and reading stdin (`cat log \| alf -p "explain"`). Without `--auto`, sensitive actions are **refused** (no prompt is possible). | `src/alf`, `Args.py` | S |
| Model list | `/model` uses the list frozen at startup (`builtin.py:115`). Add `/model refresh`. | `builtin.py` | S |
| Robustness | Timeouts (none today, so a dead host blocks indefinitely). Retries with increasing wait on connection error, 429 or 5xx, **only before the first chunk** is received. | provider | S |
| Hard-coded parameters | `MAXLOOP=10` (`HandleResponse.py:38`) and truncation at 5000 characters (`:93`) to make configurable. | `Variables.py` | S |
| Packaging | `pyproject.toml` with `[project.scripts] alf=...` to install with `pipx install`. Top-level modules (`Variables`, `Memory`, `Context`) must move into an `alf_cli/` package with relative imports. `pytest` must leave `requirements.txt` (line 5), and versions must be pinned. | all of `src/`, `tests/` (`sys.path.insert`) | M |
| CI | Python 3.10 to 3.13 matrix. CI tests 3.12, the README announces 3.10+, and the Dockerfile uses 3.14. | `.github/workflows/ci.yml` | S |

### Defects found in the code
- `src/alf:24`: `clear_terminal()` runs at import, before `if __name__`. The screen is cleared even for `--help` or an error, which will get in the way of `-p`.
- `ConnectionOllama.py:4`: the client is created at import, with no timeout or headers.
- `HandleResponse.py:87`: the list of read-only tools is hard-coded by name. `:100`: `except Exception` is too broad. `:119`: mixes `response["message"]` and `response.message` accesses, specific to Ollama.
- `Variables.py:1`: `from AlfTools import *`. In addition, the global `tools` / `available` lists are modified directly by `McpClient.py:101-105`.
- `ResponseHandle.py:188`: the system prompt does not name the MCP tools, and it is wrong when tools are disabled.

---

## Security risks to have checked
- **`--no-sandbox`.**
  - `check_command` (`Permissions.py:24-40`) is a heuristic on the words of the command. It is easy to bypass, for example with `$(printf ...)`, globs or base64.
  - `RunCommand.py:93` runs `shell=True` and **inherits the environment**. The future `ALF_API_KEY` would be readable with `env`. The environment passed to the command must be cleaned.
- **Remote model.** Data is sent in clear over `http://`. A malicious server can inject tool calls, and `--auto` mode will run them.
- **Prompt tools (1b).** A read file containing a fake ` ```tool ` block could be taken for a real tool call (prompt injection). Parse only the model's response, never the observations.
- **Remote execution (2b).** Risks on the SSH host key, SSH agent forwarding and the remote sandbox.
- **Config file.** It needs 600 permissions, and headers must never be written to logs.

---

## Branches

`CONTRIBUTING.md` asks to start from `dev`. Proposed branches:
- `feat/no-tools-fallback`
- `feat/remote-host`
- `feat/config-profiles`
- `feat/packaging`
- `feat/providers`
- `feat/prompt-tools`
- `fix/startup-smells`

---

## Proposed order

- **v0.2: unblock and make robust**
  - 1a (fallback to chat without tools);
  - 2a (host, token, TLS, timeouts, warning);
  - fix of the noted defects (`clear_terminal`, client at import, system prompt).
- **v0.3: convenience**
  - `config.toml` and profiles;
  - `-p` and stdin;
  - `/model refresh`;
  - pipx packaging and CI matrix. To be done **before** v0.4 so that imports are moved only once.
- **v0.4: multi-engine**
  - Provider abstraction, Ollama first, then the OpenAI-compatible version (llama.cpp, vLLM, LM Studio, cloud).
- **v0.5: small models**
  - 1b (prompt tools), valid for all engines;
  - `--ssh-tunnel` tunnel.
- **v0.6 (experimental)**
  - 2b (remote execution), only if there is a real need beyond "install alf on the remote machine".
