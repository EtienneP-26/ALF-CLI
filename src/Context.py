from Variables import ALERT_RATIO

CHARS_PER_TOKEN: int = 3
BASELINE_TOKENS: int = 900
REMOVED_RESULT: str = "[result removed: context budget]"


def _field(message, name: str):
    if isinstance(message, dict):
        return message.get(name)
    return getattr(message, name, None)


def _callChars(call) -> int:
    function = _field(call, "function")
    return len(str(_field(function, "name") or "")) + len(str(_field(function, "arguments") or ""))


def _messageChars(message) -> int:
    chars = len(_field(message, "content") or "")
    return chars + sum(_callChars(call) for call in _field(message, "tool_calls") or [])


def estimateTokens(messages: list) -> int:
    return sum(_messageChars(m) for m in messages) // CHARS_PER_TOKEN + BASELINE_TOKENS


def _blocks(messages: list) -> list[list]:
    blocks: list[list] = []
    for message in messages:
        if _field(message, "role") == "tool" and blocks and _field(blocks[-1][0], "tool_calls"):
            blocks[-1].append(message)
        else:
            blocks.append([message])
    return blocks


def _lastUserIndex(messages: list) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if _field(messages[index], "role") == "user":
            return index
    return -1


def _blankOldResults(messages: list, budget: int, prefix: list) -> list:
    result = list(messages)
    for index, message in enumerate(result):
        if estimateTokens(prefix + result) <= budget:
            break
        if _field(message, "role") == "tool" and _field(message, "content") != REMOVED_RESULT:
            result[index] = {"role": "tool", "tool_name": _field(message, "tool_name"), "content": REMOVED_RESULT}
    return result


def _dropOldBlocks(messages: list, budget: int, prefix: list) -> list:
    blocks = _blocks(messages)
    last = _lastUserIndex(messages)
    kept = messages[last] if last != -1 else None
    while estimateTokens(prefix + [m for b in blocks for m in b]) > budget:
        old = next((b for b in blocks if not any(m is kept for m in b)), None)
        if old is None:
            break
        blocks.remove(old)
    return [m for b in blocks for m in b]


def buildContext(history: list, summary: str, summarizedCount: int, budget: int) -> list:
    prefix = [{"role": "system", "content": f"Summary of the earlier conversation:\n{summary}"}] if summary else []
    messages = list(history[summarizedCount:])
    if estimateTokens(prefix + messages) > budget:
        messages = _blankOldResults(messages, budget, prefix)
    if estimateTokens(prefix + messages) > budget:
        messages = _dropOldBlocks(messages, budget, prefix)
    return prefix + messages


def formatKTokens(count: int) -> str:
    return f"{count / 1000:.1f}k"


def formatContext(used: int, budget: int, estimated: bool = False) -> str:
    mark = "~" if estimated else ""
    return f"Context: {mark}{formatKTokens(used)}/{formatKTokens(budget)} ({used * 100 // budget}%)"


def contextLine(used: int | None, budget: int, messages: list, turn: int | None = None, total: int = 0, hidden: int = 0) -> str:
    if used is None:
        line = formatContext(estimateTokens(messages), budget, True)
    else:
        line = formatContext(used, budget)
        if turn is not None:
            line += f" | Message: {formatKTokens(turn)} | Total: {formatKTokens(total)}"
    if hidden:
        line += f" | {hidden} older messages summarized"
    return line


def isNearBudget(used: int, budget: int) -> bool:
    return used >= ALERT_RATIO * budget
