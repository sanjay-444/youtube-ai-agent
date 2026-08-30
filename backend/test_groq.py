from app.services.groq import call_groq_json


def main():

    result = call_groq_json(
        system_prompt="Return valid JSON only.",
        user_prompt="Return a JSON object with status equal to ok.",
        max_tokens=500,
        retries=1,
    )

    print("\nRESULT:")
    print(result)


if __name__ == "__main__":
    main()