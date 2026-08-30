import ollama


MODEL_NAME = "llama3.2:3b"


def call_ollama(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2
):

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        options={
            "temperature": temperature
        }
    )

    content = response["message"]["content"]

    if not content:
        raise RuntimeError(
            "Ollama returned an empty response."
        )

    return content.strip()