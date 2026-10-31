from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
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

session = PromptSession(
    multiline=True,
    key_bindings=kb,
    completer=WordCompleter(commandNames, sentence=True),
    bottom_toolbar=HTML(" <b>Enter</b> send · <b>Alt+Enter</b> new line · <b>/help</b>"),
)

def printLogo():
    console.print(Panel(f"[bold #1800f7] {logoAlf} [/]\n[dim]Type /help for help[/]", border_style="#1800f7", expand=False))

def inputPrompt() -> str:
    console.rule(style="#1800f7")
    prompt = session.prompt(HTML("<ansired>❯ </ansired>"))
    console.rule(style="#1800f7")
    return prompt

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
    state = {"done": 0, "rest": ""}

    def onText(text: str):
        blocks, state["rest"] = splitBlocks(text[state["done"]:])
        state["done"] = len(text) - len(state["rest"])
        if not live.is_started:
            status.stop()
            live.start()
        for block in blocks:
            live.console.print(NoBgMarkdown(formatMarkdown(block)))
        live.update(tailPreview(state["rest"], max(console.height - 2, 1)))

    status.start()
    try:
        return mfunction(*args, on_text=onText, **kwargs)
    finally:
        status.stop()
        if live.is_started:
            live.stop()
            if state["rest"].strip():
                outputPrint(state["rest"])

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
