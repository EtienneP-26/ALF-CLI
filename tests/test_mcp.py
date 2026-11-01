import json
import os
import subprocess
import sys
from pathlib import Path

import ollama
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from HandleResponse import handleResponse
from AlfTools import McpClient
from AlfTools.Permissions import ALLOWED_DIRS, checkAccess

DEVTOOLS = {"command": "python3", "args": [str(ROOT / "src/McpServers/DevTools.py")]}


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("ALF_HOME", str(tmp_path / "home"))


def connect(tmp_path, servers, **kw):
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"mcpServers": servers}))
    tools, available, out = [], {}, []
    close = McpClient.connectServers(str(config), tools, available, out.append, **kw)
    return close, tools, available, out


def children():
    return subprocess.run(["pgrep", "-f", "[D]evTools.py|[h]ang_server"], capture_output=True, text=True).stdout.split()


def test_list_and_call(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n# TODO: fix\n")
    (tmp_path / ".hidden.py").write_text("# TODO: no\n")
    monkeypatch.chdir(tmp_path)
    close, tools, available, out = connect(tmp_path, {"devtools": DEVTOOLS})
    try:
        assert [t.function.name for t in tools] == ["devtools__find_todos"]
        assert "devtools__find_todos" in available
        assert "devtools" in out[0]
        assert available["devtools__find_todos"]() == "a.py:2: # TODO: fix"
    finally:
        close()
    assert children() == []


@pytest.mark.parametrize("content", ["{not json", '{"mcpServers": [1]}', '{"other": 1}', '{"mcpServers": {"a": 1}}'])
def test_bad_config(tmp_path, content):
    config = tmp_path / "bad.json"
    config.write_text(content)
    tools, out = [], []
    McpClient.connectServers(str(config), tools, {}, out.append)
    assert tools == [] and len(out) == 1


def test_missing_explicit_config_and_silent_default(tmp_path):
    out = []
    McpClient.connectServers(str(tmp_path / "nope.json"), [], {}, out.append)
    assert len(out) == 1
    out = []
    McpClient.connectServers(None, [], {}, out.append)
    assert out == []


def test_failing_server(tmp_path):
    close, tools, _, out = connect(tmp_path, {"bad": {"command": "python3", "args": ["-c", "raise SystemExit(1)"]}})
    close()
    assert tools == [] and len(out) == 1 and "failed" in out[0]


def test_hanging_server(tmp_path):
    hang = {"command": "python3", "args": ["-c", "import time; time.sleep(60)  # hang_server"]}
    close, tools, _, out = connect(tmp_path, {"hang": hang}, timeout=1)
    close()
    assert tools == [] and len(out) == 1 and "failed" in out[0]
    assert children() == []


class Fake:
    def __init__(self, name):
        self.calls = [ollama.ChatResponse(message=ollama.Message(role="assistant", tool_calls=[ollama.Message.ToolCall(function=ollama.Message.ToolCall.Function(name=name, arguments={}))])),
                      ollama.ChatResponse(message=ollama.Message(role="assistant", content="done"))]

    def think(self, fn, **kw):
        return self.calls.pop(0)


def run(auto, answer):
    ran, asked = [], []
    def tool():
        ran.append(1)
        return "x" * 6000
    def confirm(q):
        asked.append(q)
        return answer
    fake = Fake("srv__tool")
    history, *_ = handleResponse(None, "m", "hi", [], [], {"srv__tool": tool}, lambda *a: None, None, confirm,
                                 {"think": fake.think}, think=False, auto=auto)
    return history, ran, asked


def test_ask_refused():
    history, ran, asked = run(False, False)
    assert ran == [] and asked == ["Accept:"]
    assert history[-2]["content"] == "refused by the user"


def test_auto_runs_and_truncates():
    history, ran, asked = run(True, False)
    assert ran == [1] and asked == []
    assert history[-2]["content"].endswith("[truncated]") and len(history[-2]["content"]) < 5100


def test_git_write_refused_read_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr("AlfTools.Permissions.ALLOWED_DIRS", [str(tmp_path)])
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("")
    for name in ("write_file", "edit_file"):
        with pytest.raises(PermissionError):
            checkAccess(name, {"file_path": str(tmp_path / ".git" / "config")})
    checkAccess("read_file", {"file_path": str(tmp_path / ".git" / "config")})
    checkAccess("write_file", {"file_path": str(tmp_path / "ok.txt")})
