from CliTools.Cli import choiceVisual
from Commands import command, commandHelp
from Memory import listConversations, loadConversation, newConversation, renameConversation

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
    return f"Model changed for: `{state.model}`"

@command("/new", "Start a new conversation")
def newCommand(state, args):
    state.conversation = newConversation()
    state.history = []
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
    conversations = listConversations()
    if len(args) != 1 or not args[0].isdigit() or not 1 <= int(args[0]) <= len(conversations):
        return "Usage: `/resume <number>`, numbers are listed by `/conversations`"
    conversation = loadConversation(conversations[int(args[0]) - 1]["id"])
    state.conversation = conversation
    state.history = conversation["messages"]
    return f"Conversation resumed: `{conversation['title']}` ({len(state.history)} messages)"
