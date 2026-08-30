
import json

from app.services.groq import call_groq


def generate_action_items(context: str):

    if not context or not context.strip():

        return []


    system_prompt = """
You are an expert action-item extraction agent.

Analyze the YouTube transcript and extract
specific, practical actions mentioned in the video.

Do not invent actions.

Only include actions supported by the transcript.

Return ONLY valid JSON.

Do not use Markdown.

Do not use ```.

Required format:

{
    "action_items": [
        {
            "action": "Specific action",
            "details": "Details or command if available",
            "priority": "HIGH"
        }
    ]
}

Priority must be:

HIGH
MEDIUM
LOW

If no action items exist:

{
    "action_items": []
}
"""


    user_prompt = f"""
Extract all meaningful action items from this
YouTube transcript.

Focus especially on:

- Commands
- Installation steps
- Configuration steps
- Development tasks
- Implementation steps
- Testing steps
- Deployment steps
- Recommended next steps

Transcript:

{context}
"""


    try:

        result = call_groq(
            system_prompt,
            user_prompt
        )

    except Exception as error:

        print(
            f"Action Items Groq error: {error}"
        )

        return []


    if not result:

        return []


    result = result.strip()


    # --------------------------------------------------------
    # Remove Markdown fences
    # --------------------------------------------------------

    if "```json" in result:

        result = result.replace(
            "```json",
            ""
        )

    if "```" in result:

        result = result.replace(
            "```",
            ""
        )

    result = result.strip()


    # --------------------------------------------------------
    # Find JSON object if model added extra text
    # --------------------------------------------------------

    start = result.find("{")

    end = result.rfind("}")

    if start != -1 and end != -1:

        result = result[
            start:end + 1
        ]


    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:

        data = json.loads(
            result
        )

    except json.JSONDecodeError:

        print(
            "Warning: Action Items Agent returned invalid JSON."
        )

        print(
            "Raw action item response:"
        )

        print(
            result[:2000]
        )

        return []


    if not isinstance(
        data,
        dict
    ):

        return []


    items = data.get(
        "action_items",
        []
    )


    if not isinstance(
        items,
        list
    ):

        return []


    cleaned_items = []


    for item in items:

        if not isinstance(
            item,
            dict
        ):

            continue


        action = str(
            item.get(
                "action",
                ""
            )
        ).strip()


        details = str(
            item.get(
                "details",
                ""
            )
        ).strip()


        priority = str(
            item.get(
                "priority",
                "MEDIUM"
            )
        ).upper().strip()


        if not action:

            continue


        if priority not in [
            "HIGH",
            "MEDIUM",
            "LOW"
        ]:

            priority = "MEDIUM"


        cleaned_items.append(
            {
                "action": action,
                "details": details,
                "priority": priority
            }
        )


    return cleaned_items

