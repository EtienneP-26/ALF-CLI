
def list_models(client):
    models_infos = client.list()
    models_names = [m["model"] for m in models_infos.get("models", [])]
    return models_names, models_infos 

def show_models(modelnames) -> str:
    response: str = "\n"
    i = 0

    for model in modelnames:
        if i == 6:
            response += "\n"
            i = 0
        truncated_text = model[:24]
        response += f"{truncated_text:<25}"
        i += 1
    response += "\n"
    return response
