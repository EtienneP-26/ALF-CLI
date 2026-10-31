from Variables import ALERT_RATIO

CHARS_PER_TOKEN: int = 3
BASELINE_TOKENS: int = 900


def estimateTokens(messages: list) -> int:
    chars = sum(len(message.get("content") or "") for message in messages)
    return chars // CHARS_PER_TOKEN + BASELINE_TOKENS


def formatKTokens(count: int) -> str:
    return f"{count / 1000:.1f}k"


def formatContext(used: int, budget: int, estimated: bool = False) -> str:
    mark = "~" if estimated else ""
    return f"Context: {mark}{formatKTokens(used)}/{formatKTokens(budget)} ({used * 100 // budget}%)"


def contextLine(used: int | None, budget: int, messages: list) -> str:
    if used is None:
        return formatContext(estimateTokens(messages), budget, True)
    return formatContext(used, budget)


def isNearBudget(used: int, budget: int) -> bool:
    return used >= ALERT_RATIO * budget
