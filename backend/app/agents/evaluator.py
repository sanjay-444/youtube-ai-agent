
import json
import re
from typing import Any

from app.services.groq import call_groq


def _extract_json(text: str) -> dict:
    """
    Safely extract a JSON object from an LLM response.
    """

    if not text:
        raise ValueError("Empty evaluator response.")

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(
        r"```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```\s*",
        "",
        text
    )

    # Find first JSON object
    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:
        raise ValueError(
            "No JSON object found in evaluator response."
        )

    return json.loads(match.group(0))


def _fallback_evaluation(
    summary: Any,
    action_items: Any
) -> dict:
    """
    Local fallback evaluator.

    This avoids another Groq request when the evaluator
    cannot get a valid response.
    """

    score = 0

    # --------------------------------------------------------
    # Summary checks
    # --------------------------------------------------------

    if isinstance(summary, dict):

        executive_summary = summary.get(
            "executive_summary",
            ""
        )

        key_takeaways = summary.get(
            "key_takeaways",
            []
        )

        important_concepts = summary.get(
            "important_concepts",
            []
        )

        conclusion = summary.get(
            "conclusion",
            ""
        )

        if executive_summary:
            score += 3

        if isinstance(key_takeaways, list):
            if len(key_takeaways) >= 3:
                score += 2
            elif len(key_takeaways) > 0:
                score += 1

        if isinstance(important_concepts, list):
            if len(important_concepts) >= 2:
                score += 1

        if conclusion:
            score += 1

    # --------------------------------------------------------
    # Action item checks
    # --------------------------------------------------------

    if isinstance(action_items, list):

        if len(action_items) >= 5:
            score += 2
        elif len(action_items) > 0:
            score += 1

    # Maximum 10
    score = min(score, 10)

    feedback = []

    if not isinstance(summary, dict):
        feedback.append(
            "Summary is missing or invalid."
        )

    if isinstance(summary, dict):

        if not summary.get("executive_summary"):
            feedback.append(
                "Executive summary is missing."
            )

        if not summary.get("key_takeaways"):
            feedback.append(
                "Key takeaways are missing."
            )

        if not summary.get("conclusion"):
            feedback.append(
                "Conclusion is missing."
            )

    if not action_items:
        feedback.append(
            "No action items were generated."
        )

    if not feedback:
        feedback.append(
            "Summary contains the major required sections "
            "and actionable recommendations are present."
        )

    return {
        "quality_score": score,
        "summary_score": min(score, 7),
        "action_items_score": min(
            3,
            len(action_items)
            if isinstance(action_items, list)
            else 0
        ),
        "feedback": " ".join(feedback),
        "missing_information": [],
        "hallucinations": [],
        "evaluator_mode": "fallback"
    }


def evaluate_output(
    context: str,
    summary: Any,
    action_items: Any
) -> dict:
    """
    Evaluate the generated summary and action items.

    Parameters
    ----------
    context:
        Transcript/analysis context.

    summary:
        Generated summary.

    action_items:
        Generated action items.

    Returns
    -------
    dict
        Evaluation result.
    """

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not context:
        context = ""

    if summary is None:
        summary = {}

    if action_items is None:
        action_items = []

    # --------------------------------------------------------
    # Keep evaluator input small.
    #
    # We DON'T send the entire transcript again.
    # This saves Groq tokens.
    # --------------------------------------------------------

    if len(context) > 6000:
        context_for_eval = context[:6000]
    else:
        context_for_eval = context

    summary_text = json.dumps(
        summary,
        ensure_ascii=False
    )

    action_items_text = json.dumps(
        action_items,
        ensure_ascii=False
    )

    # --------------------------------------------------------
    # Prevent enormous evaluator prompts
    # --------------------------------------------------------

    if len(summary_text) > 7000:
        summary_text = summary_text[:7000]

    if len(action_items_text) > 7000:
        action_items_text = action_items_text[:7000]

    system_prompt = """
You are a strict quality evaluator for a YouTube video
analysis system.

Evaluate the generated summary and action items against
the supplied video context.

Return ONLY valid JSON.

Required JSON format:

{
  "quality_score": 0,
  "summary_score": 0,
  "action_items_score": 0,
  "feedback": "",
  "missing_information": [],
  "hallucinations": []
}

Scoring:

quality_score:
0 to 10

summary_score:
0 to 7

action_items_score:
0 to 3

Check:

1. Accuracy
2. Relevance
3. Completeness
4. Whether action items are actually actionable
5. Whether claims are supported by the context
6. Whether hallucinations exist
"""

    user_prompt = f"""
VIDEO CONTEXT:

{context_for_eval}

GENERATED SUMMARY:

{summary_text}

GENERATED ACTION ITEMS:

{action_items_text}

Evaluate the output.

Return ONLY JSON.
"""

    # --------------------------------------------------------
    # Call Groq
    # --------------------------------------------------------

    try:

        print()
        print("Groq request for evaluator...")

        result = call_groq(
            system_prompt,
            user_prompt
        )

        # ----------------------------------------------------
        # Empty response
        # ----------------------------------------------------

        if not result or not result.strip():

            print(
                "Evaluator received empty Groq response."
            )

            print(
                "Using local fallback evaluator."
            )

            return _fallback_evaluation(
                summary,
                action_items
            )

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        evaluation = _extract_json(result)

        # ----------------------------------------------------
        # Validate required fields
        # ----------------------------------------------------

        if "quality_score" not in evaluation:
            raise ValueError(
                "quality_score missing from evaluator response."
            )

        if "summary_score" not in evaluation:
            evaluation["summary_score"] = 0

        if "action_items_score" not in evaluation:
            evaluation["action_items_score"] = 0

        if "feedback" not in evaluation:
            evaluation["feedback"] = ""

        if "missing_information" not in evaluation:
            evaluation["missing_information"] = []

        if "hallucinations" not in evaluation:
            evaluation["hallucinations"] = []

        evaluation["evaluator_mode"] = "groq"

        return evaluation

    # --------------------------------------------------------
    # Any Groq / JSON failure
    # --------------------------------------------------------

    except Exception as e:

        print(
            f"Evaluator Groq error: "
            f"{type(e).__name__}: {e}"
        )

        print(
            "Using local fallback evaluator."
        )

        return _fallback_evaluation(
            summary,
            action_items
        )

