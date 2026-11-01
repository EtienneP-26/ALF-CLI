import re

from OllamaTools.ResponseHandle import getResponse
from OllamaTools.StreamHandle import EmptyResponseError
from Variables import DEFAULT_MAX_TOKENS
from AlfTools.Permissions import checkAccess
from AlfTools.FileManipulation import applyEdit

def countTokens(response) -> int | None:
    prompt = getattr(response, "prompt_eval_count", None)
    generated = getattr(response, "eval_count", None)
    if prompt is None and generated is None:
        return None
    return int(prompt or 0) + int(generated or 0)

def countGenerated(response) -> int | None:
    generated = getattr(response, "eval_count", None)
    return None if generated is None else int(generated)

def  handleResponse(
    client, 
    model: str,
    prompt: str,
    history: list[dict],
    tools: list,
    available: dict, 
    printfunc,
    difffunc,
    validationfunc,
    visualfuncs: dict,
    think: bool = True,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    summary: str = "",
    summarizedCount: int = 0,
    auto: bool = False,
) -> tuple[list[dict], int | None, int | None]:

    MAXLOOP = 10
    loop = 0
    history.append({"role": "user", "content": prompt})
    written = []
    def ask(callTools=tools, notice=None):
        response = visualfuncs["think"](getResponse, client=client, model=model, history=history, tools=callTools, think=think, max_tokens=max_tokens, summary=summary, summarizedCount=summarizedCount, notice=notice)
        written.append(countGenerated(response))
        return response
    response = ask()

    while response.message.tool_calls:
        if loop >= MAXLOOP:
            response = ask(callTools=[], notice="Max tools loop call reached please wrap that up no more tool call for this loop")
            break
        response.message.thinking = None
        history.append(response.message)
        added = len(history)
        for call in response.message.tool_calls or []:
            toolfunc = available.get(call.function.name)
            if toolfunc is None:
                history.append({
                    "role": "tool",
                    "tool_name": call.function.name, 
                    "content": f"{call.function.name} does not exist",
                })
                continue
            args = call.function.arguments
            try:
                checkAccess(call.function.name, args)
            except PermissionError as e:
                printfunc(f"`{call.function.name}` refused: {e}")
                history.append({"role": "tool", "tool_name": call.function.name, "content": f"{e}"})
                continue
            if call.function.name in ("write_file", "edit_file"):
                try:
                    new = applyEdit(args.get("file_path", ""), args.get("old_text", ""), args.get("new_text", "")) if call.function.name == "edit_file" else args.get("content", "")
                except (ValueError, OSError, TypeError) as e:
                    printfunc(f"`{call.function.name}` failed: {e}")
                    history.append({"role": "tool", "tool_name": call.function.name, "content": f"{e}"})
                    continue
                diff = difffunc(args.get("file_path", ""), new)
                printfunc(f"`{call.function.name}` → `{args.get('file_path')}`\n```diff\n{diff}\n```")
            elif call.function.name == "web_search":
                if think:
                    printfunc(f"Action: web_search({args})")
            elif call.function.name == "plan_task":
                printfunc("Plan:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(args.get("steps", []), 1)))
            else:
                printfunc(f"{'Action: ' if think else ''}{call.function.name}({args})")
            if call.function.name in ("read_file", "list_dir", "web_search") or auto or validationfunc(f"Accept:"):
                try:
                    if call.function.name == "web_search":
                        result = visualfuncs["websearch"](toolfunc, **call.function.arguments)
                    else: 
                        result = toolfunc(**call.function.arguments)
                    if len(result) > 5000:
                        result = result[:5000] + "[truncated]" 
                    history.append({
                        "role": "tool",
                        "tool_name": call.function.name, 
                        "content": f"{result}",
                    })
                except Exception as e:
                    history.append({
                        "role": "tool",
                        "tool_name": call.function.name, 
                        "content": f"{e}",
                    })  
            else:
                history.append({
                    "role": "tool",
                    "tool_name": call.function.name, 
                    "content": f"refused by the user",
                })
        if think:
            for message in history[added:]:
                visualfuncs["observation"](message["tool_name"], message["content"])
        response = ask()
        loop += 1

    marker = r"(\s*<\|[^>]*>\s*)+"
    if re.fullmatch(marker, response["message"]["content"] or ""):
        response = ask(callTools=[])
        if re.fullmatch(marker, response["message"]["content"] or ""):
            raise EmptyResponseError("The model answered with only a raw marker.")
    history.append({"role": "assistant", "content": response["message"]["content"]})

    known = [n for n in written if n is not None]
    return history, countTokens(response), sum(known) if known else None
