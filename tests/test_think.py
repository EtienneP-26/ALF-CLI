import os
import sys
from types import SimpleNamespace

import pytest
from ollama import ChatResponse, Message

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from CliTools import Cli
from CliTools.Args import parseArgs
from Commands import State, handleCommand
import Commands.builtin as builtin
from HandleResponse import handleResponse
from Memory import _serialize
from OllamaTools.StreamHandle import EmptyResponseError, collectStream
from prompt_toolkit.formatted_text import fragment_list_to_text, to_formatted_text


def chunk(content="", thinking=None, tool_calls=None):
    return ChatResponse(model="m", message=Message(role="assistant", content=content, thinking=thinking, tool_calls=tool_calls))


def toolCall(name, **arguments):
    return Message.ToolCall(function=Message.ToolCall.Function(name=name, arguments=arguments))


class FakeClient:
    """Plays one scripted stream per chat() call and records what was sent."""
    def __init__(self, streams, capabilities=("completion", "thinking")):
        self.streams, self.sent, self.capabilities = list(streams), [], list(capabilities)

    def chat(self, **kwargs):
        self.sent.append([m if isinstance(m, dict) else m.model_dump() for m in kwargs["messages"]])
        return iter(self.streams.pop(0))

    def show(self, model):
        return SimpleNamespace(capabilities=self.capabilities)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("ALF_HOME", str(tmp_path))
    Cli.thoughts.clear()
    Cli.fold["open"] = False


def run(client, history, think, printed, observed, tools_available=None, prompt="hi"):
    return handleResponse(
        client=client, model="m", prompt=prompt, history=history, tools=[], available=tools_available or {},
        printfunc=printed.append, difffunc=None, validationfunc=lambda q: True,
        visualfuncs={"think": lambda f, *a, **k: f(*a, **k), "websearch": lambda f, **k: f(**k),
                     "ask": None, "observation": lambda n, c: observed.append((n, c))},
        think=think, auto=True,
    )


def toolTurn(result, name="list_dir", **arguments):
    client = FakeClient([[chunk(thinking="plan it", tool_calls=[toolCall(name, **(arguments or {"path": "."}))])],
                         [chunk(thinking="done", content="ok")]])
    printed, observed = [], []
    run(client, [], True, printed, observed, {name: lambda **k: result})
    return printed, observed


def test_no_thinking_in_sent_history_or_serialized():
    streams = [[chunk(thinking="secret1"), chunk(content="a")],
               [chunk(thinking="secret2"), chunk(content="b")]]
    client, history = FakeClient(streams), []
    run(client, history, True, [], [], prompt="one")
    run(client, history, True, [], [], prompt="two")
    assert "secret" not in str(client.sent)
    assert "secret" not in str(_serialize(history))
    assert all("thinking" not in m for m in _serialize(history))


def test_thinking_not_kept_on_tool_call_message():
    history = []
    client = FakeClient([[chunk(thinking="why", tool_calls=[toolCall("list_dir", path=".")])], [chunk(content="ok")]])
    run(client, history, True, [], [], {"list_dir": lambda **k: "x"})
    assert "why" not in str(_serialize(history))
    assert "why" not in str(client.sent[1])


def test_thinking_only_stream_is_empty():
    with pytest.raises(EmptyResponseError):
        collectStream(iter([chunk(thinking="hmm")]))


def test_on_thinking_gets_accumulated_text():
    seen = []
    collectStream(iter([chunk(thinking="a"), chunk(thinking="b"), chunk(content="x")]), on_thinking=seen.append)
    assert seen == ["a", "ab"]


def test_think_flag():
    assert parseArgs(["--think"]).think is True
    assert parseArgs([]).think is False


def makeState():
    return State(model="m", modelNames=["m", "plain"])


def test_think_on_off_supported(monkeypatch):
    monkeypatch.setattr(builtin, "client", FakeClient([]))
    state = makeState()
    assert "on" in handleCommand("/think on", state) and state.think
    assert "off" in handleCommand("/think off", state) and not state.think


def test_think_on_unsupported(monkeypatch):
    monkeypatch.setattr(builtin, "client", FakeClient([], capabilities=["completion"]))
    state = makeState()
    assert handleCommand("/think on", state) == "Model `m` does not support thinking. Try another with `/model`."
    assert not state.think


def test_think_capability_error_means_off(monkeypatch):
    class Broken(FakeClient):
        def show(self, model):
            raise ConnectionError("down")
    monkeypatch.setattr(builtin, "client", Broken([]))
    state = makeState()
    assert "does not support" in handleCommand("/think on", state)


def test_think_menu_and_usage(monkeypatch):
    monkeypatch.setattr(builtin, "client", FakeClient([]))
    monkeypatch.setattr(builtin, "choiceVisual", lambda *a, **k: "on")
    state = makeState()
    assert state.think is False
    handleCommand("/think", state)
    assert state.think
    assert "Usage" in handleCommand("/think maybe", state)


def test_model_downgrade_turns_thinking_off(monkeypatch):
    monkeypatch.setattr(builtin, "client", FakeClient([], capabilities=["completion"]))
    monkeypatch.setattr(builtin, "resolveMaxTokens", lambda c, m: 4096)
    state = makeState()
    state.think = True
    message = handleCommand("/model plain", state)
    assert not state.think and "Thinking turned off" in message


def test_off_has_no_action_or_observation():
    client = FakeClient([[chunk(tool_calls=[toolCall("list_dir", path=".")])], [chunk(content="ok")]])
    printed, observed = [], []
    run(client, [], False, printed, observed, {"list_dir": lambda **k: "x"})
    assert observed == []
    assert not any("Action:" in p for p in printed)
    assert any(p.startswith("list_dir(") for p in printed)


def test_on_has_action_and_observation():
    printed, observed = toolTurn("a\nb\nc")
    assert any(p.startswith("Action: list_dir(") for p in printed)
    assert observed == [("list_dir", "a\nb\nc")]


def test_web_search_action_only_when_thinking():
    printed, observed = toolTurn("r", name="web_search", query="q")
    assert any(p.startswith("Action: web_search(") for p in printed)


def test_hostile_tool_result(capsys):
    printed, observed = toolTurn("[/]\x1b[31mred\x1b]0;title\x07 [bold]x")
    for name, content in observed:
        Cli.observationVisual(name, content)
    out = capsys.readouterr().out
    assert "\x1b[31m" not in out and "\x1b]0" not in out and "\x07" not in out
    assert "[/]" in out
    Cli.observationVisual("evil\x1b[1m", "")
    Cli.observationVisual("t", "x" * 500)


def test_observation_format(capsys):
    Cli.observationVisual("run_command", "a" * 300 + "\nsecond\nthird")
    out = capsys.readouterr().out.replace("\n", "")
    assert "Observation: run_command · 3 lines · " + "a" * 100 in out
    assert "a" * 101 not in out


def test_think_visual_collects_and_prints(capsys):
    def fake(on_text, on_thinking):
        on_thinking("l1\nl2")
        on_text("answer\n\n")
    Cli.thinkVisual(fake)
    assert Cli.thoughts == ["l1\nl2"]
    assert "Thought · 2 lines · Ctrl+O to open, /think show" in capsys.readouterr().out


def test_think_visual_survives_empty_response(capsys):
    def fake(on_text, on_thinking):
        on_thinking("only thinking")
        raise EmptyResponseError("empty")
    with pytest.raises(EmptyResponseError):
        Cli.thinkVisual(fake)
    assert Cli.thoughts == ["only thinking"]


def test_think_show(monkeypatch):
    state = makeState()
    assert "No reasoning" in handleCommand("/think show", state)
    Cli.thoughts.extend(["first\x1b[0m", "second"])
    out = handleCommand("/think show", state)
    assert "first" in out and "second" in out and "\x1b" not in out


def text(value):
    return fragment_list_to_text(to_formatted_text(value))


def test_toolbar_closed_and_open():
    assert "Alt+Enter" in text(Cli.bottomToolbar())
    Cli.thoughts.append("word " * 400 + "\x1b[31m")
    assert "Alt+Enter" in text(Cli.bottomToolbar())
    Cli.fold["open"] = True
    bar = text(Cli.bottomToolbar())
    assert "Ctrl+O to close" in bar and "\x1b" not in bar
    assert len(bar.splitlines()) <= 13
    Cli.fold["open"] = False


def plain(value):
    return value.plain


def test_think_view_open_and_closed():
    hostile = "[/] [bold]x\x1b[31m y"
    closed = plain(Cli.thinkView(hostile, False))
    assert "Ctrl+O to show the reasoning" in closed and "[/]" not in closed
    opened = plain(Cli.thinkView(hostile, True))
    assert "[/] [bold]x" in opened and "\x1b" not in opened and "Ctrl+O to close" in opened
    many = plain(Cli.thinkView("\n".join(f"w{i}" for i in range(200)) + "end", True))
    assert len(many.splitlines()) <= 15


@pytest.fixture
def pty_pair():
    import pty
    master, slave = pty.openpty()
    yield master, slave
    os.close(master)
    os.close(slave)


def waitFor(check):
    import time
    for _ in range(100):
        if check():
            return True
        time.sleep(0.02)
    return False


def test_ctrl_o_toggles_live_open(pty_pair):
    import termios
    master, slave = pty_pair
    before = termios.tcgetattr(slave)
    calls = []
    Cli.liveOpen = False
    stop = Cli.startKeys(lambda: calls.append(1), slave)
    try:
        assert stop is not None
        assert not termios.tcgetattr(slave)[3] & termios.IEXTEN
        os.write(master, b"\x0f")
        assert waitFor(lambda: Cli.liveOpen)
        os.write(master, b"a\x0f")
        assert waitFor(lambda: not Cli.liveOpen)
    finally:
        stop()
    assert termios.tcgetattr(slave) == before


def test_termios_restored_after_exception(pty_pair, monkeypatch):
    import termios
    master, slave = pty_pair
    before = termios.tcgetattr(slave)
    monkeypatch.setattr(Cli.sys, "stdin", open(slave, closefd=False))

    def fake(on_text, on_thinking):
        on_thinking("hmm")
        assert termios.tcgetattr(slave) != before
        raise RuntimeError("boom")
    with pytest.raises(RuntimeError):
        Cli.thinkVisual(fake)
    assert termios.tcgetattr(slave) == before


def test_listener_stops_before_content(pty_pair, monkeypatch):
    import termios
    master, slave = pty_pair
    before = termios.tcgetattr(slave)
    monkeypatch.setattr(Cli.sys, "stdin", open(slave, closefd=False))
    seen = []

    def fake(on_text, on_thinking):
        on_thinking("hmm")
        on_text("answer\n\n")
        seen.append(termios.tcgetattr(slave) == before)
    Cli.thinkVisual(fake)
    assert seen == [True]


def test_no_listener_without_tty_or_thinking(monkeypatch):
    started = []
    monkeypatch.setattr(Cli.threading, "Thread", lambda *a, **k: started.append(1))
    assert Cli.startKeys(lambda: None) is None
    Cli.thinkVisual(lambda on_text, on_thinking: on_text("x\n\n"))
    assert started == []


def test_model_option_parsed_and_default():
    assert parseArgs(["--model", "x"]).model == "x"
    assert parseArgs([]).model == "gemma4:e2b-mt"


def test_model_menu_interrupt_keeps_model(monkeypatch):
    def cancel(*a, **k):
        raise KeyboardInterrupt
    monkeypatch.setattr(builtin, "choiceVisual", cancel)
    state = SimpleNamespace(model="m", modelNames=["m", "n"], maxTokensFixed=True, contextUsed=None, think=False)
    builtin.modelCommand(state, [])
    assert state.model == "m"


def test_main_has_no_84_and_uses_client_for_keep_alive():
    src = open(os.path.join(os.path.dirname(__file__), "..", "src", "alf")).read()
    assert "84" not in src and "ollama.generate" not in src


def test_marker_only_answer_is_retried_once():
    client, history = FakeClient([[chunk(content="<|tool_response>")], [chunk(content="real answer")]]), []
    run(client, history, False, [], [])
    assert history[-1] == {"role": "assistant", "content": "real answer"}
