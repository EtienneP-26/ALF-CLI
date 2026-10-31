import httpx
import ollama
from Variables import DEFAULT_MAX_TOKENS


def modelContextLength(client, model: str) -> int | None:
    try:
        info = client.show(model).modelinfo or {}
    except (ollama.ResponseError, ConnectionError, httpx.HTTPError):
        return None
    for key, value in info.items():
        if key.endswith(".context_length") and isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
    return None


def resolveMaxTokens(client, model: str) -> int:
    return modelContextLength(client, model) or DEFAULT_MAX_TOKENS
