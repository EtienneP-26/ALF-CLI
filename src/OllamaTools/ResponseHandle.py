
SystemPrompt: str = """you are an Agentic CLI assistant named ALF-CLI.
    Your response will be shown in a markdown view in a terminal."""

def getResponse(
    client, 
    model: str,
    prompt: str,
    history: str,
    think: bool = True
) -> str:    
    Response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SystemPrompt},
            {"role": "history", "content": history},
            {"role": "user", "content": prompt},
        ],
        think=think,
    )
    Response = Response["message"]["content"]
    return Response
