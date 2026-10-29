from dataclasses import dataclass, field
from typing import Callable
from Memory import newConversation

@dataclass
class State:
    model: str
    modelNames: list[str]
    running: bool = True
    conversation: dict = field(default_factory=newConversation)
    history: list = field(default_factory=list)

    def resume(self, conversation: dict):
        self.conversation = conversation
        self.history = conversation["messages"]

_commands: dict[str, tuple[Callable, str]] = {}

def command(name: str, help: str):
    def register(func: Callable) -> Callable:
        _commands[name] = (func, help)
        return func
    return register

def commandNames() -> list[str]:
    return list(_commands)

def commandHelp() -> dict[str, str]:
    return {name: help for name, (_, help) in _commands.items()}

def handleCommand(entry: str, state: State) -> str | None:
    words = entry.split()
    if not words or not words[0].startswith("/"):
        return None
    if words[0] not in _commands:
        return f"Unknown command `{words[0]}`. Type `/help` to list them."
    func, _ = _commands[words[0]]
    return func(state, words[1:])
