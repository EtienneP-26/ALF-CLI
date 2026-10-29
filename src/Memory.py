import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone

DIR = os.path.expanduser(os.getenv("ALF_HOME", "~/.alf"))
CONVERSATIONS_DIR = os.path.join(DIR, "conversations")
TITLE_MAX_LENGTH = 50
ID_PATTERN = re.compile(r"[0-9a-f]{32}")


def _now() -> str:
    """# Current UTC time as an ISO 8601 string

    ## Returns:
        The time with a second precision, e.g. `2026-10-27T11:42:00+00:00`.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(conversationId: str) -> str:
    """# Path of the file holding a conversation

    ## Args:
        conversationId: Id of the conversation (32 hex characters).

    ## Returns:
        The path of `<conversationId>.json` inside the conversations folder.

    ## Raises:
        ValueError: If the id is not 32 hex characters (blocks path traversal).

    ## Example:
        >>> _path("../etc/passwd")
        Traceback (most recent call last):
        ValueError: Invalid conversation id: '../etc/passwd'
    """
    if not isinstance(conversationId, str) or not ID_PATTERN.fullmatch(conversationId):
        raise ValueError(f"Invalid conversation id: {conversationId!r}")
    return os.path.join(CONVERSATIONS_DIR, f"{conversationId}.json")


def _cleanTitle(text: str) -> str:
    """# Make a text usable as a one-line title

    ## Args:
        text: Any text, e.g. the first message of the user.

    ## Returns:
        The text on one line, cut to `TITLE_MAX_LENGTH` characters with `…` if too long.

    ## Example:
        >>> _cleanTitle("  hello \\n  world ")
        'hello world'
    """
    title = " ".join(text.split())
    if len(title) > TITLE_MAX_LENGTH:
        return title[:TITLE_MAX_LENGTH - 1].rstrip() + "…"
    return title


def _titleFromMessages(messages: list[dict]) -> str:
    """# Title built from the first user message

    ## Args:
        messages: Messages of the conversation, as dicts.

    ## Returns:
        The cleaned content of the first user message, or "" if there is none.
    """
    for message in messages:
        if message.get("role") == "user":
            return _cleanTitle(str(message.get("content", "")))
    return ""


def _serialize(messages: list) -> list[dict]:
    """# Turn messages into JSON-friendly dicts

    ## Args:
        messages: Dicts or ollama `Message` objects.

    ## Returns:
        The messages as plain dicts.
    """
    return [m if isinstance(m, dict) else m.model_dump(exclude_none=True, mode="json") for m in messages]


def _isValid(data, conversationId: str) -> bool:
    """# Check that file content looks like a conversation

    ## Args:
        data: Parsed JSON of a conversation file.
        conversationId: Id the file is supposed to hold.

    ## Returns:
        True if the metadata and the messages have the expected types.
    """
    return (
        isinstance(data, dict)
        and data.get("id") == conversationId
        and all(isinstance(data.get(key), str) for key in ("title", "created_at", "updated_at"))
        and isinstance(data.get("messages"), list)
        and all(isinstance(m, dict) for m in data["messages"])
    )


def _write(conversation: dict):
    """# Save a conversation file without ever leaving it half written

    The data goes to a temporary file first, then replaces the real one.
    A failure only prints a warning, so the chat keeps going.

    ## Args:
        conversation: The conversation (metadata and messages) to save.
    """
    path = _path(conversation["id"])
    try:
        os.makedirs(DIR, mode=0o700, exist_ok=True)
        os.makedirs(CONVERSATIONS_DIR, mode=0o700, exist_ok=True)
        with open(f"{path}.tmp", "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False)
        os.replace(f"{path}.tmp", path)
    except (OSError, TypeError, ValueError) as e:
        print(f"Warning: cannot save conversation {conversation['id']}: {e}", file=sys.stderr)


def newConversation() -> dict:
    """# Start an empty conversation

    Nothing is written to disk until the first `saveConversation`.

    ## Returns:
        A dict with `id`, `title` (empty), `created_at`, `updated_at` and `messages`.
    """
    now = _now()
    return {"id": uuid.uuid4().hex, "title": "", "created_at": now, "updated_at": now, "messages": []}


def saveConversation(conversation: dict, messages: list):
    """# Save the whole conversation to its own file

    Updates `updated_at`, and sets the title from the first user message
    if the conversation has no title yet.

    ## Args:
        conversation: A conversation from `newConversation` or `loadConversation`.
        messages: Every message of the conversation (dicts or ollama `Message`).
    """
    conversation["messages"] = _serialize(messages)
    conversation["updated_at"] = _now()
    if not conversation["title"]:
        conversation["title"] = _titleFromMessages(conversation["messages"])
    _write(conversation)


def loadConversation(conversationId: str) -> dict | None:
    """# Read one conversation from disk

    ## Args:
        conversationId: Id of the conversation (32 hex characters).

    ## Returns:
        The conversation, or None if the file is missing or not a valid conversation.

    ## Raises:
        ValueError: If the id is not 32 hex characters.
    """
    path = _path(conversationId)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if _isValid(data, conversationId) else None


def renameConversation(conversationId: str, title: str) -> str:
    """# Change the title of a conversation

    The last activity date is left untouched.

    ## Args:
        conversationId: Id of the conversation (32 hex characters).
        title: The new title, cleaned to one line and cut if too long.

    ## Returns:
        The title as saved.

    ## Raises:
        ValueError: If the id is invalid, the conversation does not exist or the title is empty.
    """
    conversation = loadConversation(conversationId)
    if conversation is None:
        raise ValueError(f"Unknown conversation: {conversationId}")
    title = _cleanTitle(title)
    if not title:
        raise ValueError("Title cannot be empty")
    conversation["title"] = title
    _write(conversation)
    return title


def listConversations() -> list[dict]:
    """# List the saved conversations, most recent activity first

    ## Returns:
        The metadata (`id`, `title`, `created_at`, `updated_at`) of each valid
        conversation. Unreadable files are skipped.
    """
    try:
        names = os.listdir(CONVERSATIONS_DIR)
    except OSError:
        return []
    conversations = []
    for name in names:
        stem, extension = os.path.splitext(name)
        if extension != ".json" or not ID_PATTERN.fullmatch(stem):
            continue
        conversation = loadConversation(stem)
        if conversation is not None:
            conversation.pop("messages")
            conversations.append(conversation)
    return sorted(conversations, key=lambda c: c["updated_at"], reverse=True)


def findConversation(reference: str) -> dict | None:
    if ID_PATTERN.fullmatch(reference):
        return loadConversation(reference)
    conversations = listConversations()
    if reference.isdigit() and 1 <= int(reference) <= len(conversations):
        return loadConversation(conversations[int(reference) - 1]["id"])
    return None
