from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from Variables import logoAlf, listCommands

console = Console()
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
    # history=FileHistory(".cli_history"),
    multiline=True,
    key_bindings=kb,
    completer=WordCompleter(listCommands, sentence=True),
    bottom_toolbar=HTML(" <b>Enter</b> envoyer · <b>Alt+Enter</b> nouvelle ligne · <b>/help</b>"),
)

def printLogo():
    console.print(Panel(f"[bold #1800f7] {logoAlf} [/]\n[dim]Tape /help pour l'aide[/]", border_style="#1800f7", expand=False))

def inputPrompt() -> str:
    prompt = session.prompt(HTML("<ansired>❯ </ansired>"))
    return prompt

def thinkVisual(mfunction, *args, **kwargs):
    with console.status("[dim]Réflexion…[/]", spinner="dots", spinner_style="#1800f7"):
        response = mfunction(*args, **kwargs)
    return response

def outputPrint(response: str, color: str | None = None):
    console.print(Markdown(response), style=color)

def choiceVisual(message: str, options: list[str], default: str) -> str:
    choice_options = [(option, option.capitalize()) for option in options]
    result = choice(
        message=message,
        options=choice_options,
        default=default,
    )

    return result
