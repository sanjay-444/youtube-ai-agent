import json

from app.services.groq import call_groq


def generate_action_items(
    transcript: str
):
    """
    Extract and consolidate actionable tasks
    from the compressed transcript analysis.
    """

    system_prompt = """
You are an expert action-item extraction agent.

The input contains summaries, key points, and
action candidates extracted from a YouTube video.

Your job is to produce a final list of useful,
specific, actionable tasks.

IMPORTANT:

- Use ONLY information present in the input.
- Do not hallucinate.
- Do not invent tasks.
- Consolidate duplicate actions.
- Prefer concrete technical tasks.
- Return valid JSON only.
"""


    user_prompt = f"""
Analyze the following video analysis.

The video may contain technical instructions,
commands, installation steps, configuration steps,
coding steps, testing steps, and deployment steps.

Extract the most useful actions that a viewer
could perform after watching the video.

Return EXACTLY this structure:

{{
    "action_items": [
        {{
            "action": "Specific action",
            "priority": "HIGH",
            "reason": "Evidence from the video analysis"
        }}
    ]
}}

RULES:

1. Maximum 10 action items.

2. Remove duplicate actions.

3. Actions must be concrete.

4. Installation instructions are actions.

5. Configuration instructions are actions.

6. Coding instructions are actions.

7. Testing instructions are actions.

8. Deployment instructions are actions.

9. Commands explicitly demonstrated are actions.

10. Do not convert general explanations into actions.

11. Do not invent anything.

12. Priority must be exactly:
   HIGH
   MEDIUM
   LOW

13. Return an empty list ONLY when there are
    genuinely no actionable tasks.

VIDEO ANALYSIS:

{transcript}
"""


    result = call_groq(
        system_prompt,
        user_prompt
    )


    print(
        "\nRaw Action Agent response:"
    )

    print(result)


    # --------------------------------------------------
    # Parse JSON
    # --------------------------------------------------

    try:

        data = json.loads(
            result
        )

    except json.JSONDecodeError:

        try:

            start = result.find("{")
            end = result.rfind("}") + 1

            if start != -1 and end > start:

                data = json.loads(
                    result[start:end]
                )

            else:

                print(
                    "Action Agent did not return JSON."
                )

                return {
                    "action_items": []
                }

        except Exception as e:

            print(
                "Action parsing failed:",
                str(e)
            )

            return {
                "action_items": []
            }


    # --------------------------------------------------
    # Validate
    # --------------------------------------------------

    if not isinstance(
        data,
        dict
    ):

        return {
            "action_items": []
        }


    actions = data.get(
        "action_items",
        []
    )


    if not isinstance(
        actions,
        list
    ):

        return {
            "action_items": []
        }


    cleaned_actions = []


    for item in actions:

        if not isinstance(
            item,
            dict
        ):
            continue


        action = item.get(
            "action",
            ""
        )

        priority = item.get(
            "priority",
            "MEDIUM"
        )

        reason = item.get(
            "reason",
            ""
        )


        if not action:

            continue


        action = str(
            action
        ).strip()


        priority = str(
            priority
        ).upper().strip()


        reason = str(
            reason
        ).strip()


        if priority not in [
            "HIGH",
            "MEDIUM",
            "LOW"
        ]:

            priority = "MEDIUM"


        cleaned_actions.append({

            "action": action,

            "priority": priority,

            "reason": reason

        })


    # --------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------

    unique_actions = []

    seen = set()


    for item in cleaned_actions:

        normalized = (
            item["action"]
            .lower()
            .strip()
        )


        if normalized in seen:

            continue


        seen.add(
            normalized
        )

        unique_actions.append(
            item
        )


    return {
        "action_items": unique_actions[:10]
    }