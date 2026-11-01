import asyncio
import atexit
import json
import logging
import os
import sys
import threading
from concurrent.futures import Future, wait
from pathlib import Path

import ollama

START_TIMEOUT = 30
CALL_TIMEOUT = 60

def alfHome():
    return Path(os.environ.get("ALF_HOME", Path.home() / ".alf"))

def readConfig(path, printfunc):
    explicit = path is not None
    file = Path(path) if explicit else alfHome() / "mcp_servers.json"
    try:
        servers = json.loads(file.read_text())["mcpServers"]
        if not isinstance(servers, dict):
            raise TypeError("`mcpServers` must be an object")
        return servers
    except FileNotFoundError:
        if explicit:
            printfunc(f"MCP config not found: `{file}`")
    except (OSError, ValueError, KeyError, TypeError) as e:
        printfunc(f"MCP config ignored: {e!r}")
    return {}

def toText(result):
    text = "\n".join(getattr(c, "text", f"[{c.type} omitted]") for c in result.content)
    return f"Error: {text}" if result.is_error else text

def rootCause(e):
    while isinstance(e, BaseExceptionGroup):
        e = e.exceptions[0]
    return str(e) or type(e).__name__

def connectServers(path, tools, available, printfunc, timeout=START_TIMEOUT):
    servers = readConfig(path, printfunc)
    if not servers:
        return lambda: None
    import anyio
    from mcp import ClientSession, StdioServerParameters, stdio_client
    logging.getLogger("mcp").setLevel(logging.CRITICAL)
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    scopes = []
    alfHome().mkdir(parents=True, exist_ok=True)
    errlog = open(alfHome() / "mcp.log", "a")

    async def serve(params, ready):
        try:
            with anyio.CancelScope() as scope:
                scopes.append(scope)
                async with stdio_client(params, errlog=errlog) as (read, write), ClientSession(read, write) as session:
                    with anyio.fail_after(timeout):
                        await session.initialize()
                        found = (await session.list_tools()).tools
                    ready.set_result((session, found))
                    await anyio.sleep_forever()
        except Exception as e:
            if not ready.done():
                ready.set_exception(e)

    def forward(session, name):
        def call(**args):
            future = asyncio.run_coroutine_threadsafe(session.call_tool(name, args, read_timeout_seconds=CALL_TIMEOUT), loop)
            try:
                return toText(future.result())
            finally:
                future.cancel()
        return call

    started, tasks = {}, []
    for name, config in servers.items():
        try:
            params = StdioServerParameters(**config)
        except (TypeError, ValueError):
            printfunc(f"MCP `{name}` skipped: invalid config")
            continue
        if params.command in ("python", "python3"):
            params.command = sys.executable
        started[name] = Future()
        tasks.append(asyncio.run_coroutine_threadsafe(serve(params, started[name]), loop))

    for name, ready in started.items():
        try:
            session, found = ready.result()
        except (Exception, KeyboardInterrupt) as e:
            printfunc(f"MCP `{name}` failed: {rootCause(e)}")
            continue
        names = []
        for t in found:
            full = f"{name}__{t.name}"
            try:
                tools.append(ollama.Tool.model_validate({"type": "function", "function": {"name": full, "description": t.description or "", "parameters": t.input_schema}}))
            except ValueError:
                printfunc(f"MCP `{name}`: tool `{t.name}` skipped: unsupported schema")
                continue
            available[full] = forward(session, t.name)
            names.append(t.name)
        printfunc(f"MCP `{name}`: {', '.join(names) or 'no tools'}")

    def close():
        for scope in scopes:
            loop.call_soon_threadsafe(scope.cancel)
        wait(tasks, timeout=8)
    atexit.register(close)
    return close
