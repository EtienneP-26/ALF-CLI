from typing import Callable, Iterable

from ollama import ChatResponse

class EmptyResponseError(Exception):
    pass

def collectStream(
    stream: Iterable[ChatResponse],
    on_text: Callable[[str], None] | None = None,
    on_thinking: Callable[[str], None] | None = None,
) -> ChatResponse:
    """
    # collectStream

    Consume a streamed `chat()` and rebuild one complete response, same shape as `stream=False`.

    ## Args
    - `stream`: the chunks returned by `client.chat(..., stream=True)`.
    - `on_text`: called with the full text received so far each time a chunk brings new text.
    - `on_thinking`: same as `on_text`, for the reasoning text.

    ## Returns
    The last chunk (it holds the token counts), with the whole `content`, `thinking` and `tool_calls` put back in its message.

    ## Example
    ```python
    response = collectStream(client.chat(model=m, messages=msgs, stream=True), on_text=print)
    response.message.tool_calls
    ```
    """
    content, thinking, tool_calls = "", "", []
    last = None
    for chunk in stream:
        last = chunk
        if chunk.message.thinking:
            thinking += chunk.message.thinking
            if on_thinking:
                on_thinking(thinking)
        tool_calls.extend(chunk.message.tool_calls or [])
        if chunk.message.content:
            content += chunk.message.content
            if on_text:
                on_text(content)
    if last is None or not (content.strip() or tool_calls):
        raise EmptyResponseError(
            "The model stopped without answering: the context is probably full. "
            "Use `/new` or raise `--max-tokens`."
        )
    last.message.content = content
    last.message.thinking = thinking or None
    last.message.tool_calls = tool_calls or None
    return last
