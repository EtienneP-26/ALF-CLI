from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import choice
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown, CodeBlock
from rich.syntax import Syntax
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich.segment import Segment, Segments
from difflib import unified_diff
from os import path
import os
from Variables import logoAlf
from Commands import commandNames
import select
import sys
import textwrap
import threading
try:
    import termios
    import tty
except ImportError:
    termios = None

thoughts: list[str] = []
fold = {"open": False}
liveOpen = False

class NoBgCodeBlock(CodeBlock):
    def __rich_console__ (self, console, options):
        code = str(self.text).rstrip()
        if self.lexer_name == "diff":
            out = Text()
            for line in code.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    out.append(line + "\n", style="green on #0d2b0d")
                elif line.startswith("-") and not line.startswith("---"):
                    out.append(line + "\n", style="red on #2b0d0d")
                elif line.startswith("@@"):
                    out.append(line + "\n", style="cyan")
                else:
                    out.append(line + "\n")
            yield out
            return
        yield Syntax(code, self.lexer_name, theme=self.theme, word_wrap=True, padding=1, background_color="default")

class NoBgMarkdown(Markdown):
    elements = {**Markdown.elements, "fence": NoBgCodeBlock, "code_block": NoBgCodeBlock}

def splitBlocks(text: str) -> tuple[list[str], str]:
    blocks, current, fence, consumed, pos = [], [], False, 0, 0
    for line in text.splitlines(keepends=True):
        if not line.endswith("\n"):
            break
        pos += len(line)
        if line.strip().startswith("```"):
            current.append(line)
            if fence:
                blocks.append("".join(current))
                current, consumed = [], pos
            fence = not fence
        elif not fence and not line.strip():
            if current:
                blocks.append("".join(current))
            current, consumed = [], pos
        else:
            current.append(line)
    return blocks, text[consumed:]

def tailPreview(rest: str, height: int):
    lines = console.render_lines(NoBgMarkdown(formatMarkdown(rest)), console.options.update(height=None), pad=False)
    segments = []
    for line in lines[-height:]:
        segments += line + [Segment.line()]
    return Segments(segments[:-1])

console = Console(theme=Theme({
    "markdown.code": "bold cyan",
    "markdown.code_block": "none",
}))
kb = KeyBindings()


@kb.add("enter")
def _(event):
    """
    Entrée = envoyer
    """
    event.current_buffer.validate_and_handle()

@kb.add("escape", "enter")
def _(event):
    """
    Alt+Entrée = nouvelle ligne
    """
    event.current_buffer.insert_text("\n")

@kb.add("c-o")
def _(event):
    """
    Ctrl+O = open or close the last reasoning in the toolbar
    """
    if thoughts:
        fold["open"] = not fold["open"]
        event.app.invalidate()

def printable(text: str) -> str:
    return "".join(c if c == "\n" or c.isprintable() else " " for c in text)

def bottomToolbar():
    if fold["open"] and thoughts:
        lines = textwrap.wrap(printable(thoughts[-1]).replace("\n", " "), max(console.width - 2, 20))
        return " Thought (Ctrl+O to close)\n " + "\n ".join(lines[-12:])
    return HTML(" <b>Enter</b> send · <b>Alt+Enter</b> new line · <b>/help</b>")

session = PromptSession(
    multiline=True,
    key_bindings=kb,
    completer=WordCompleter(commandNames, sentence=True),
    bottom_toolbar=bottomToolbar,
    style=Style.from_dict({"bottom-toolbar": "noreverse #888888"}),
)

def printLogo():
    console.print(Panel(f"[bold #1800f7] {logoAlf} [/]\n[dim]Type /help for help[/]", border_style="#1800f7", expand=False))

def inputPrompt() -> str:
    console.rule(style="#1800f7")
    fold["open"] = False
    prompt = session.prompt(HTML("<ansired>❯ </ansired>"))
    console.rule(style="#1800f7")
    return prompt

def thinkView(thought: str, isOpen: bool) -> Text:
    out = Text("Thinking…", style="dim")
    if isOpen:
        lines = textwrap.wrap(printable(thought).replace("\n", " "), max(console.width - 2, 20))
        out.append("\n" + "\n".join(lines[-12:]) + "\nCtrl+O to close", style="dim")
    else:
        out.append("\nCtrl+O to show the reasoning", style="dim")
    return out

def startKeys(onToggle, fd: int | None = None):
    """Listen for Ctrl+O on stdin in a thread; return a stop function, or None if not possible."""
    if termios is None:
        return None
    try:
        fd = sys.stdin.fileno() if fd is None else fd
        if not os.isatty(fd):
            return None
        saved = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        attrs = termios.tcgetattr(fd)
        attrs[3] &= ~termios.IEXTEN
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
    except (ValueError, OSError, termios.error):
        return None
    stop = threading.Event()

    def loop():
        global liveOpen
        while not stop.is_set():
            try:
                if select.select([fd], [], [], 0.05)[0]:
                    data = os.read(fd, 64)
                    if not data:
                        return
                    for byte in data:
                        if byte == 0x0f:
                            liveOpen = not liveOpen
                            onToggle()
            except (OSError, ValueError):
                return

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

    def stopKeys():
        stop.set()
        thread.join()
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)

    return stopKeys

def thinkVisual(mfunction, *args, **kwargs):
    """
    # thinkVisual

    Spinner while the model thinks, then live markdown as its answer streams in.

    ## Args
    - `mfunction`: the call to run; it must accept an `on_text` callback.

    ## Returns
    Whatever `mfunction` returns.
    """
    status = console.status("[dim]Thinking…[/]", spinner="dots2", spinner_style="#1800f7")
    live = Live(console=console, refresh_per_second=15, vertical_overflow="crop", transient=True)
    state = {"done": 0, "rest": "", "index": None, "shown": False, "keys": None, "listen": True}

    def stopKeys():
        state["listen"] = False
        if state["keys"]:
            stop, state["keys"] = state["keys"], None
            stop()

    def refresh():
        status.update(thinkView(thoughts[state["index"]], liveOpen))

    def onThinking(text: str):
        if state["index"] is None:
            thoughts.append(text)
            state["index"] = len(thoughts) - 1
        else:
            thoughts[state["index"]] = text
        if state["listen"] and state["keys"] is None:
            state["keys"] = startKeys(refresh)
        if state["keys"]:
            refresh()

    def showThought():
        if state["index"] is not None and not state["shown"]:
            state["shown"] = True
            count = len(thoughts[state["index"]].splitlines())
            console.print(f"[dim]Thought · {count} lines · Ctrl+O to open, /think show[/]")

    def onText(text: str):
        stopKeys()
        blocks, state["rest"] = splitBlocks(text[state["done"]:])
        state["done"] = len(text) - len(state["rest"])
        if not live.is_started:
            status.stop()
            showThought()
            live.start()
        for block in blocks:
            live.console.print(NoBgMarkdown(formatMarkdown(block)))
        live.update(tailPreview(state["rest"], max(console.height - 2, 1)))

    status.start()
    try:
        return mfunction(*args, on_text=onText, on_thinking=onThinking, **kwargs)
    finally:
        stopKeys()
        status.stop()
        showThought()
        if live.is_started:
            live.stop()
            if state["rest"].strip():
                outputPrint(state["rest"])

def observationVisual(name: str, content: str):
    lines = content.splitlines()
    first = printable(lines[0].strip())[:100] if lines else ""
    console.print(Text(f"Observation: {printable(name).replace(chr(10), " ")} · {len(lines)} lines · {first}", style="dim"))

def webSearchVisual(mfunction, *args, **kwargs):
    with console.status("[dim]Searching the web…[/]", spinner="earth", spinner_style="#013220"):
        response = mfunction(*args, **kwargs)
    return response

def compressVisual(mfunction, *args, **kwargs):
    with console.status("[dim]Compressing the context…[/]", spinner="aesthetic", spinner_style="#1800f7"):
        return mfunction(*args, **kwargs)

def formatMarkdown(response: str) -> str:
    if "```" not in response:
        response = response.replace("\n", "  \n")
    return response

def outputPrint(response: str, color: str | None = None):
    console.print(NoBgMarkdown(formatMarkdown(response)), style=color)

def choiceVisual(message: str, options: list[str], default: str) -> str:
    choice_options = [(option, option.capitalize()) for option in options]
    result = choice(
        message=message,
        options=choice_options,
        default=default,
    )

    return result

def confirmVisual(question: str) -> bool:
    return choiceVisual(f"\n{question}\n", ["yes", "no"], "no") == "yes"

def write_diff(file_path: str, content: str) -> str:
    old_file = ""
    if path.exists(file_path):
        with open(file_path, encoding="utf-8") as f:
            old_file = f.read()
    return "\n".join(unified_diff(old_file.splitlines(), content.splitlines(), fromfile=f"a/{file_path}", tofile=f"b/{file_path}", lineterm="",))

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')
