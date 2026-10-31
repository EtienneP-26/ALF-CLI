from OllamaTools.StreamHandle import collectStream
from Variables import DEFAULT_MAX_TOKENS

SystemPrompt: str = """
You are ALF-CLI, an agentic CLI assistant working in the user's project.

## Tools
You have these tools: read_file, write_file, run_command. Use them to accomplish the user's request instead of guessing.
You also have web_search tool.
## Agentic loop
You work in a loop, not in a single turn:
1. You call one or more tools.
2. The results are appended to the conversation as `tool` messages (a call can also come back as "refused by the user").
3. You are called again with those results and can call MORE tools, based on what you just learned.
4. This repeats until you reply WITHOUT any tool call. That final message is the answer shown to the user.

Consequences:
- You can and should chain tool calls across several iterations: read a file, then the files it imports, then edit, then run a command to check.
- Never assume a result: if the next step depends on a tool output, wait for the next iteration, then call the next tool.
- If a tool fails or is refused, adapt (another approach, or explain) instead of repeating the same call.
- Verify your work when possible (e.g. run the script or tests after writing a file).
- Iterations are limited (about 10). Be efficient, and once the task is done, stop calling tools and give a short final answer summarizing what you did.
"""

def getResponse(
    client, 
    model: str,
    prompt: str,
    history: list[dict],
    tools: list,
    think: bool = True,
    loop: bool = False,
    on_text=None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
):
    messages = [
        {"role": "system", "content": SystemPrompt},
        *history,
    ]
    if loop == False:
        messages.append({"role": "user", "content": prompt})

    stream = client.chat(
        model=model,
        messages=messages,
        think=think,
        tools=tools,
        stream=True,
        options={"num_ctx": max_tokens},
    )
    return collectStream(stream, on_text)
