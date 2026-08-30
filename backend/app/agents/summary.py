import json

from app.services.groq import call_groq


def generate_summary(analysis_context: str):

    if not analysis_context:
        return {
            "executive_summary": "",
            "key_takeaways": [],
            "important_concepts": [],
            "action_items": [],
            "conclusion": ""
        }

    # Keep the final prompt reasonably small
    MAX_CONTEXT = 12000

    if len(analysis_context) > MAX_CONTEXT:
        analysis_context = analysis_context[:MAX_CONTEXT]

    print(
        f"\nFinal analysis context length: "
        f"{len(analysis_context)} characters"
    )

    system_prompt = """
You are an expert YouTube video analysis agent.

Analyze the supplied transcript information.

Rules:
- Use ONLY the supplied information.
- Do not hallucinate.
- Do not use external information.
- Extract concrete action items.
- Return valid JSON only.
- Do not use Markdown.
- Do not wrap the JSON in ```.

The JSON must contain:
executive_summary
key_takeaways
important_concepts
action_items
conclusion
"""

    user_prompt = f"""
Analyze this YouTube video information.

Return exactly this JSON structure:

{{
    "executive_summary": "A concise summary of the entire video.",

    "key_takeaways": [
        "Important lesson 1",
        "Important lesson 2"
    ],

    "important_concepts": [
        "Concept 1",
        "Concept 2"
    ],

    "action_items": [
        {{
            "action": "Specific task to perform",
            "priority": "HIGH",
            "reason": "Why this task is useful"
        }}
    ],

    "conclusion": "Practical conclusion from the video."
}}

IMPORTANT:

For action_items, extract actual tasks from the video.

For example, if the video says:

- Install Python
- Create virtual environment
- Install FastAPI
- Run uvicorn
- Create PostgreSQL database
- Test API

then those should become action items.

Do NOT return an empty action_items array if the
supplied information contains actionable instructions.

Keep the response concise.

VIDEO INFORMATION:

{analysis_context}
"""

    print(
        "\n[4] Running Final Analysis Agent..."
    )

    try:

        result = call_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=1800
        )

    except Exception as e:

        print(
            f"\nFinal analysis failed: {e}"
        )

        return {
            "executive_summary": "",
            "key_takeaways": [],
            "important_concepts": [],
            "action_items": [],
            "conclusion": ""
        }

    if not result:

        print(
            "\nFinal analysis returned empty response."
        )

        return {
            "executive_summary": "",
            "key_takeaways": [],
            "important_concepts": [],
            "action_items": [],
            "conclusion": ""
        }

    print(
        "\nRaw Final Analysis response:"
    )

    print(result)

    # Remove Markdown code fences if model adds them
    result = result.strip()

    if result.startswith("```json"):
        result = result[7:]

    elif result.startswith("```"):
        result = result[3:]

    if result.endswith("```"):
        result = result[:-3]

    result = result.strip()

    # ============================================================
    # PARSE JSON
    # ============================================================

    try:

        data = json.loads(result)

    except json.JSONDecodeError:

        print(
            "\nDirect JSON parsing failed."
        )

        # Try extracting JSON object
        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:

            try:

                data = json.loads(
                    result[start:end + 1]
                )

            except Exception as e:

                print(
                    f"\nJSON extraction failed: {e}"
                )

                data = {
                    "executive_summary": result,
                    "key_takeaways": [],
                    "important_concepts": [],
                    "action_items": [],
                    "conclusion": ""
                }

        else:

            data = {
                "executive_summary": result,
                "key_takeaways": [],
                "important_concepts": [],
                "action_items": [],
                "conclusion": ""
            }

    # ============================================================
    # VALIDATE DATA
    # ============================================================

    executive_summary = data.get(
        "executive_summary",
        ""
    )

    key_takeaways = data.get(
        "key_takeaways",
        []
    )

    important_concepts = data.get(
        "important_concepts",
        []
    )

    action_items = data.get(
        "action_items",
        []
    )

    conclusion = data.get(
        "conclusion",
        ""
    )

    # Ensure correct types

    if not isinstance(
        key_takeaways,
        list
    ):
        key_takeaways = []

    if not isinstance(
        important_concepts,
        list
    ):
        important_concepts = []

    if not isinstance(
        action_items,
        list
    ):
        action_items = []

    # ============================================================
    # CLEAN ACTION ITEMS
    # ============================================================

    cleaned_actions = []

    for item in action_items:

        if isinstance(item, dict):

            action = str(
                item.get(
                    "action",
                    ""
                )
            ).strip()

            priority = str(
                item.get(
                    "priority",
                    "MEDIUM"
                )
            ).upper().strip()

            reason = str(
                item.get(
                    "reason",
                    ""
                )
            ).strip()

            if priority not in [
                "HIGH",
                "MEDIUM",
                "LOW"
            ]:
                priority = "MEDIUM"

            if action:

                cleaned_actions.append({
                    "action": action,
                    "priority": priority,
                    "reason": reason
                })

    # ============================================================
    # FINAL RESULT
    # ============================================================

    final_result = {

        "executive_summary": str(
            executive_summary
        ).strip(),

        "key_takeaways": [
            str(item).strip()
            for item in key_takeaways
            if str(item).strip()
        ][:8],

        "important_concepts": [
            str(item).strip()
            for item in important_concepts
            if str(item).strip()
        ][:10],

        "action_items": cleaned_actions[:10],

        "conclusion": str(
            conclusion
        ).strip()
    }

    print(
        "\n[4] Final analysis generated."
    )

    print(
        f"Action items generated: "
        f"{len(cleaned_actions)}"
    )

    return final_result