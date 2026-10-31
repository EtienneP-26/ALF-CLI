import httpx
import ollama

from Context import BASELINE_TOKENS, CHARS_PER_TOKEN, buildContext, estimateTokens, _field
from Memory import saveConversation
from Variables import COMPACT_RATIO

KEEP_MESSAGES: int = 6
INSTRUCTION: str = (
    "You write the memory of a conversation between a user and an assistant. "
    "Answer with a short list that keeps: the user's goal, the decisions, the files touched, "
    "the errors met, the constraints and the work remaining. "
    "Always copy verbatim every fact the user asked to remember or gave (codes, secrets, names, numbers, paths). "
    "If a previous summary is given, keep all of its content and add the new information. "
    "Do not copy the assistant's long answers, keep the list under 15 lines. Do not invent anything. Write in the same language as the conversation. Answer with the list only."
)
REMINDER: str = "Now write the updated list. Keep every verbatim fact (codes, names, numbers, paths) from the previous summary and the conversation."


def _clip(text: str, size: int) -> str:
    return text if len(text) <= size else text[:max(size - 5, 0)] + "[...]"


def _parts(message) -> tuple[str, str, str]:
    role = _field(message, "role")
    calls = [str(_field(_field(c, "function"), "name")) for c in _field(message, "tool_calls") or []]
    suffix = f" [tools: {', '.join(calls)}]" if calls else ""
    return f"{role}: ", _field(message, "content") or "", suffix


def _shares(sizes: list[int], space: int) -> list[int]:
    shares = [0] * len(sizes)
    for k, i in enumerate(sorted(range(len(sizes)), key=sizes.__getitem__)):
        shares[i] = min(sizes[i], space // (len(sizes) - k))
        space -= shares[i]
    return shares


def summaryInput(oldSummary: str, messages: list, budget: int) -> str:
    room = int((budget - budget // 8 - BASELINE_TOKENS - 400) * CHARS_PER_TOKEN * 0.8)
    old = _clip(oldSummary, room // 3)
    parts = [_parts(m) for m in messages]
    head = (f"Previous summary:\n{old}\n\n" if old else "") + "Conversation:\n"
    fixed = len(head) + len(REMINDER) + 2 + sum(len(p) + len(x) + 1 for p, _, x in parts)
    shares = _shares([len(c) for _, c, _ in parts], max(room - fixed, 0))
    transcript = "\n".join(p + _clip(c, n) + x for (p, c, x), n in zip(parts, shares))
    return f"{head}{transcript}\n\n{REMINDER}"


def summarize(client, model: str, oldSummary: str, messages: list, budget: int) -> str:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": summaryInput(oldSummary, messages, budget)},
        ],
        think=False,
        stream=False,
        options={"num_ctx": budget, "num_predict": budget // 8},
    )
    return (response.message.content or "").strip()


def findCut(history: list, start: int, prompt: dict, limit: int) -> int:
    cuts = [i for i in range(start + 1, len(history)) if _field(history[i], "role") == "user"] + [len(history)]
    for cut in cuts:
        if cut >= len(history) - KEEP_MESSAGES and estimateTokens([*history[cut:], prompt]) <= limit:
            return cut
    return len(history)


def compactIfNeeded(client, model: str, conversation: dict, history: list, prompt: str, budget: int, printfunc, visual=lambda f, *a: f(*a)) -> None:
    entry = {"role": "user", "content": prompt}
    limit = COMPACT_RATIO * budget
    summary, start = conversation["summary"], conversation["summarizedCount"]
    if estimateTokens(buildContext([*history, entry], summary, start, budget)) <= limit:
        return
    cut = findCut(history, start, entry, limit)
    if cut <= start:
        return
    try:
        newSummary = visual(summarize, client, model, summary, history[start:cut], budget)
    except (ollama.ResponseError, ConnectionError, httpx.HTTPError):
        newSummary = ""
    conversation["summarizedCount"] = cut
    if newSummary:
        conversation["summary"] = newSummary
        printfunc(f"Older messages summarized ({cut - start} messages).")
    else:
        printfunc(f"Could not summarize: {cut - start} older messages are no longer sent.")
    saveConversation(conversation, history)
