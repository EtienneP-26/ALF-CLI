from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice
from rich.console import Console
from rich.markdown import Markdown, CodeBlock
from rich.syntax import Syntax
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from difflib import unified_diff
from os import path
from Variables import logoAlf, listCommands

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
    completer=WordCompleter(listCommands, sentence=True),
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
    with console.status("[dim]Thinking…[/]", spinner="dots2", spinner_style="#1800f7"):
        response = mfunction(*args, **kwargs)
    return response

def webSearchVisual(mfunction, *args, **kwargs):
    with console.status("[dim]Searching the web…[/]", spinner="earth", spinner_style="#013220"):
        response = mfunction(*args, **kwargs)
    return response

def outputPrint(response: str, color: str | None = None):
    if "```" not in response:
        response = response.replace("\n", "  \n")
    console.print(NoBgMarkdown(response), style=color)

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

