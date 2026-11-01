from CliTools.Cli import thoughts, printable, choiceVisual, printLogo, clear_terminal
from Commands import command, commandHelp
from Context import contextLine
from OllamaTools.ConnectionOllama import client
from OllamaTools.ModelContext import resolveMaxTokens, supportsThinking
from Memory import deleteConversation, findConversation, listConversations, newConversation, renameConversation

@command("/exit", "Quit ALF-CLI")
def exitCommand(state, args):
    state.running = False
    return ""

@command("/help", "List the commands")
def helpCommand(state, args):
    return "\n".join(f"- `{name}`: {help}" for name, help in commandHelp().items())

@command("/model", "Change the model: `/model` to choose, `/model <name>` to set")
def modelCommand(state, args):
    if not args:
        state.model = choiceVisual("\nChose a model: ", state.modelNames, state.model)
    elif args[0] in state.modelNames:
        state.model = args[0]
    else:
        return f"Model `{args[0]}` not available"
    if not state.maxTokensFixed:
        state.maxTokens = resolveMaxTokens(client, state.model)
    state.contextUsed = None
    message = f"Model changed for: `{state.model}`"
    if state.think and not supportsThinking(client, state.model):
        state.think = False
        message += "\nThinking turned off: this model does not support it."
    return message

@command("/new", "Start a new conversation")
def newCommand(state, args):
    state.conversation = newConversation()
    state.history = []
    state.contextUsed = None
    state.totalTokens = 0
    clear_terminal()
    printLogo()
    return "New conversation started"

@command("/rename", "Rename the current conversation: `/rename <title>`")
def renameCommand(state, args):
    if not args:
        return "Usage: `/rename <title>`"
    if not state.history:
        return "Nothing to rename yet: send a message first"
    try:
        state.conversation["title"] = renameConversation(state.conversation["id"], " ".join(args))
    except ValueError as e:
        return str(e)
    return f"Conversation renamed: `{state.conversation['title']}`"

@command("/conversations", "List the saved conversations, most recent first")
def conversationsCommand(state, args):
    conversations = listConversations()
    if not conversations:
        return "No saved conversation yet"
    return "\n".join(
        f"{number}. {c['title'] or '(untitled)'} · {c['updated_at'][:16].replace('T', ' ')}"
        for number, c in enumerate(conversations, 1)
    )

@command("/resume", "Resume a saved conversation: `/resume <number>` (see `/conversations`)")
def resumeCommand(state, args):
    conversation = findConversation(args[0]) if len(args) == 1 else None
    if conversation is None:
        return "Usage: `/resume <number>`, numbers are listed by `/conversations`"
    state.resume(conversation)
    return f"Conversation resumed: `{conversation['title']}` ({len(state.history)} messages)\n{contextLine(None, state.maxTokens, state.contextMessages(), total=state.totalTokens, hidden=state.conversation['summarizedCount'])}"

def _confirm(question: str) -> bool:
    try:
        return input(question).strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False

@command("/delete", "Delete a saved conversation: `/delete <number>` (see `/conversations`)")
def deleteCommand(state, args):
    if len(args) != 1:
        return "Usage: `/delete <number>`, numbers are listed by `/conversations`"
    conversation = findConversation(args[0])
    if conversation is None:
        return f"Conversation `{args[0]}` not found"
    if not _confirm(f"Delete `{conversation['title'] or '(untitled)'}`? [y/N] "):
        return "Deletion cancelled"
    if not deleteConversation(conversation["id"]):
        return "Cannot delete the conversation"
    if conversation["id"] == state.conversation["id"]:
        newCommand(state, [])
    return f"Conversation deleted: `{conversation['title']}`"

@command("/mode", "Choose or set the mode: `/mode [ask|auto]`")
def modeCommand(state, args):
    """Open a choice menu without argument, else set the mode to ask or auto."""
    if not args:
        try:
            state.mode = choiceVisual(f"\nChoose a mode (current: {state.mode}): ", ["ask", "auto"], state.mode)
        except (EOFError, KeyboardInterrupt):
            print()
        return f"Mode: `{state.mode}`"
    if args[0] not in ("ask", "auto"):
        return "Usage: `/mode [ask|auto]`"
    state.mode = args[0]
    return f"Mode: `{state.mode}`"

@command("/think", "Show the reasoning of the model: `/think [on|off]`, `/think show` for the last one")
def thinkCommand(state, args):
    if args == ["show"]:
        if not thoughts:
            return "No reasoning for the last question. Turn it on with `/think on`."
        return printable("\n\n".join(thoughts))
    if not args:
        try:
            choiceValue = choiceVisual(f"\nThinking (current: {'on' if state.think else 'off'}): ", ["on", "off"], "on" if state.think else "off")
        except (EOFError, KeyboardInterrupt):
            print()
            return f"Thinking: `{'on' if state.think else 'off'}`"
        args = [choiceValue]
    if args[0] not in ("on", "off"):
        return "Usage: `/think [on|off|show]`"
    if args[0] == "on" and not supportsThinking(client, state.model):
        state.think = False
        return f"Model `{state.model}` does not support thinking. Try another with `/model`."
    state.think = args[0] == "on"
    return f"Thinking: `{args[0]}`"
