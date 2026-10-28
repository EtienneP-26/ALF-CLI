from CliTools.Cli import choiceVisual
from Commands import command, commandHelp
from Memory import newConversation, renameConversation

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
