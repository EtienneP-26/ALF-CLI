from OllamaTools.ResponseHandle import getResponse

def countTokens(response) -> int:
    return int(getattr(response, "prompt_eval_count", None) or 0) + int(getattr(response, "eval_count", None) or 0)

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
) -> tuple[list[dict], int]:

    MAXLOOP = 10
    loop = 0
    total_token_used: int = 0
    response = visualfuncs["think"](getResponse, client=client, model=model, prompt=prompt, history=history, tools=tools, think=think)
    history.append({"role": "user", "content": prompt})

    while response.message.tool_calls:
        if loop >= MAXLOOP:
            prompt = "Max tools loop call reached please wrap that up no more tool call for this loop"
            response = visualfuncs["think"](getResponse, client=client, model=model, prompt=prompt, history=history, tools=[], think=think)
            break
        history.append(response.message)
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
            if call.function.name == "write_file":
                diff = difffunc(args.get("file_path", ""), args.get("content", ""))
                printfunc(f"`write_file` → `{args.get('file_path')}`\n```diff\n{diff}\n```")
            elif call.function.name == "web_search":
                pass
            else:
                printfunc(f"{call.function.name}({args})")
            if call.function.name in ("read_file", "web_search") or validationfunc(f"Accept:"):
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
        total_token_used += countTokens(response)
        response = visualfuncs["think"](getResponse, client=client, model=model, prompt=prompt, history=history, tools=tools, think=think, loop=True)
        loop += 1

    history.append({"role": "assistant", "content": response["message"]["content"]})

    total_token_used += countTokens(response)
    return history, total_token_used
