from dataclasses import dataclass, field
from typing import Callable
from Context import buildContext
from Memory import newConversation
from Variables import DEFAULT_MAX_TOKENS

@dataclass
class State:
    model: str
    modelNames: list[str]
    running: bool = True
    conversation: dict = field(default_factory=newConversation)
    history: list = field(default_factory=list)
    maxTokens: int = DEFAULT_MAX_TOKENS
    maxTokensFixed: bool = False
    contextUsed: int | None = None
    totalTokens: int = 0
    mode: str = "ask"

    def resume(self, conversation: dict):
        self.conversation = conversation
        self.history = conversation["messages"]
        self.contextUsed = None
        summary, count = conversation.get("summary"), conversation.get("summarizedCount")
        conversation["summary"] = summary if isinstance(summary, str) else ""
        valid = isinstance(count, int) and not isinstance(count, bool)
        conversation["summarizedCount"] = min(max(count, 0), len(self.history)) if valid else 0
        total = conversation.get("totalTokens")
        conversation["totalTokens"] = self.totalTokens = total if isinstance(total, int) and not isinstance(total, bool) and total > 0 else 0

    def contextMessages(self) -> list:
        return buildContext(self.history, self.conversation.get("summary", ""), self.conversation.get("summarizedCount", 0), self.maxTokens)

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
