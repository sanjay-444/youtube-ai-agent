import json
import re
from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, END

from app.services.youtube import get_youtube_transcript
from app.services.groq import call_groq_json
from app.services.pdf_generator import generate_pdf


# ============================================================
# AGENT STATE
# ============================================================

class AgentState(TypedDict, total=False):

    youtube_url: str

    transcript: str

    analysis_context: str

    summary: Dict[str, Any]

    action_items: List[Any]

    evaluation: Dict[str, Any]

    quality_score: float

    pdf_path: str


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_string(value: Any) -> str:

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    return str(value)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text: str) -> str:

    if not text:
        return ""

    text = str(text)

    # Remove markdown fences
    text = text.replace("```json", "")
    text = text.replace("```", "")

    # Remove problematic characters
    text = text.replace("■", "-")
    text = text.replace("□", "-")
    text = text.replace("�", "-")

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# ROBUST JSON EXTRACTION
# ============================================================

def extract_json_result(result: Any) -> Dict[str, Any]:

    if result is None:
        raise RuntimeError(
            "Groq returned an empty response."
        )

    # --------------------------------------------------------
    # Already a dictionary
    # --------------------------------------------------------

    if isinstance(result, dict):

        return result

    # --------------------------------------------------------
    # LangChain response object
    # --------------------------------------------------------

    if hasattr(result, "content"):

        result = result.content

    text = clean_text(result)

    if not text:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    # --------------------------------------------------------
    # First attempt: direct JSON
    # --------------------------------------------------------

    try:

        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:

        pass

    # --------------------------------------------------------
    # Extract JSON object
    # --------------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:

        raise RuntimeError(
            "Groq response does not contain a JSON object."
        )

    json_text = text[start:end + 1]

    # --------------------------------------------------------
    # Second attempt
    # --------------------------------------------------------

    try:

        parsed = json.loads(json_text)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError as exc:

        print()
        print("=" * 70)
        print("INVALID GROQ JSON")
        print("=" * 70)
        print(json_text[:5000])
        print("=" * 70)

        raise RuntimeError(
            f"Invalid JSON returned by Groq: {exc}"
        )

    raise RuntimeError(
        "Groq returned invalid JSON."
    )


# ============================================================
# NODE 1
# GET YOUTUBE TRANSCRIPT
# ============================================================

def transcript_node(
    state: AgentState
) -> Dict[str, Any]:

    print()
    print("[1] Extracting YouTube transcript...")

    youtube_url = safe_string(
        state.get("youtube_url")
    ).strip()

    if not youtube_url:

        raise RuntimeError(
            "YouTube URL is required."
        )

    print(
        "Using transcript function: "
        "app.services.youtube.get_youtube_transcript"
    )

    try:

        transcript = get_youtube_transcript(
            youtube_url
        )

    except Exception as exc:

        print()
        print("Transcript retrieval failed:")
        print(str(exc))

        raise RuntimeError(
            f"Transcript retrieval failed: {exc}"
        )

    transcript = safe_string(
        transcript
    ).strip()

    if not transcript:

        raise RuntimeError(
            "YouTube transcript is empty."
        )

    print(
        f"Transcript received: "
        f"{len(transcript)} characters"
    )

    return {
        "transcript": transcript
    }


# ============================================================
# NODE 2
# PREPARE ANALYSIS CONTEXT
# ============================================================

def context_node(
    state: AgentState
) -> Dict[str, Any]:

    print()
    print("[2] Preparing analysis context...")

    transcript = safe_string(
        state.get("transcript")
    ).strip()

    if not transcript:

        raise RuntimeError(
            "Transcript is unavailable."
        )

    print(
        f"Transcript length: "
        f"{len(transcript)} characters"
    )

    # ========================================================
    # IMPORTANT
    #
    # Your Groq organization currently has:
    #
    # TPM LIMIT = 8000
    #
    # 10,000 characters was still close to the limit.
    #
    # Use 5,000 characters to keep the request safely below
    # the limit.
    # ========================================================

    MAX_CONTEXT_CHARS = 5000

    if len(transcript) > MAX_CONTEXT_CHARS:

        print(
            f"Limiting transcript to "
            f"{MAX_CONTEXT_CHARS} characters."
        )

        transcript = transcript[
            :MAX_CONTEXT_CHARS
        ]

    context = transcript.strip()

    print(
        f"Analysis context prepared: "
        f"{len(context)} characters"
    )

    return {
        "analysis_context": context
    }


# ============================================================
# NODE 3
# GENERATE SUMMARY
# ============================================================

def summary_node(
    state: AgentState
) -> Dict[str, Any]:

    print()
    print("[3] Generating AI summary...")

    context = safe_string(
        state.get("analysis_context")
    ).strip()

    if not context:

        raise RuntimeError(
            "Analysis context is empty."
        )

    # ========================================================
    # VERY STRICT JSON PROMPT
    # ========================================================

    system_prompt = """
You are a YouTube video analysis AI.

Analyze the transcript.

IMPORTANT:
Return ONLY valid JSON.

Do NOT use Markdown.
Do NOT use ```json.
Do NOT add explanations.
Do NOT add extra fields.

The JSON MUST have exactly these fields:

{
  "title": "string",
  "executive_summary": "string",
  "key_points": [
    "string",
    "string",
    "string",
    "string",
    "string"
  ],
  "conclusion": "string"
}

Rules:

1. title must be a short title.
2. executive_summary must be 2-3 sentences.
3. key_points must contain exactly 5 short points.
4. conclusion must be one short paragraph.
5. Do not create action_items here.
6. Do not create evaluation here.
7. Do not create important_concepts.
8. Do not create topics.
9. Do not create any additional fields.
10. Do not invent information.
11. Only use information supported by the transcript.
12. Make sure every opening [ has a matching ].
13. Make sure every opening { has a matching }.
14. Make sure the final response is valid JSON.
"""

    user_prompt = f"""
Analyze this YouTube transcript.

TRANSCRIPT:

{context}
"""

    try:

        print(
            "Calling Groq for video analysis..."
        )

        result = call_groq_json(
            system_prompt,
            user_prompt
        )

    except Exception as exc:

        print()
        print(
            f"Summary generation failed: {exc}"
        )

        raise RuntimeError(
            f"Summary generation failed: {exc}"
        )

    try:

        summary = extract_json_result(
            result
        )

    except Exception as exc:

        print()
        print(
            f"Could not parse summary JSON: {exc}"
        )

        raise RuntimeError(
            f"Could not parse summary JSON: {exc}"
        )

    # ========================================================
    # NORMALIZE SUMMARY
    # ========================================================

    title = safe_string(
        summary.get(
            "title",
            "YouTube Video Analysis"
        )
    )

    executive_summary = safe_string(
        summary.get(
            "executive_summary",
            ""
        )
    )

    key_points = summary.get(
        "key_points",
        []
    )

    conclusion = safe_string(
        summary.get(
            "conclusion",
            ""
        )
    )

    if not isinstance(
        key_points,
        list
    ):

        key_points = []

    # Keep maximum 5
    key_points = key_points[:5]

    # Convert every point to string
    clean_points = []

    for point in key_points:

        if isinstance(
            point,
            dict
        ):

            # Prevent nested malformed structures
            point = (
                point.get(
                    "text",
                    ""
                )
            )

        point = safe_string(
            point
        ).strip()

        if point:

            clean_points.append(
                point
            )

    summary = {

        "title": title.strip(),

        "executive_summary":
            executive_summary.strip(),

        "key_points":
            clean_points,

        "conclusion":
            conclusion.strip()
    }

    print()
    print(
        "AI summary generated successfully."
    )

    print(
        f"Title: {summary['title']}"
    )

    print(
        f"Key points: "
        f"{len(summary['key_points'])}"
    )

    return {
        "summary": summary
    }


# ============================================================
# NODE 4
# GENERATE ACTION ITEMS
# ============================================================

def action_items_node(
    state: AgentState
) -> Dict[str, Any]:

    print()
    print("[4] Generating action items...")

    summary = state.get(
        "summary",
        {}
    )

    # ========================================================
    # IMPORTANT
    #
    # Do NOT send the entire transcript again.
    #
    # This saves tokens and avoids TPM problems.
    # ========================================================

    summary_text = json.dumps(
        summary,
        ensure_ascii=False
    )

    system_prompt = """
You are an expert YouTube content analyst.

Generate practical action items from the video summary.

Return ONLY valid JSON.

Use EXACTLY this structure:

{
  "action_items": [
    {
      "action": "string",
      "priority": "HIGH"
    }
  ]
}

Rules:

1. Maximum 3 action items.
2. priority must be HIGH, MEDIUM, or LOW.
3. Do not add reason.
4. Do not add any other fields.
5. Do not use Markdown.
6. Return valid JSON only.
7. If there are no useful actions, return:
   {"action_items":[]}
"""

    user_prompt = f"""
Generate practical action items from this video summary:

{summary_text}
"""

    try:

        result = call_groq_json(
            system_prompt,
            user_prompt
        )

    except Exception as exc:

        print(
            f"Action item generation failed: {exc}"
        )

        # Don't kill entire PDF generation
        return {
            "action_items": []
        }

    try:

        parsed = extract_json_result(
            result
        )

    except Exception as exc:

        print(
            f"Action item JSON parsing failed: {exc}"
        )

        return {
            "action_items": []
        }

    action_items = parsed.get(
        "action_items",
        []
    )

    if not isinstance(
        action_items,
        list
    ):

        action_items = []

    action_items = action_items[:3]

    cleaned_items = []

    for item in action_items:

        if not isinstance(
            item,
            dict
        ):

            continue

        action = safe_string(
            item.get(
                "action",
                ""
            )
        ).strip()

        priority = safe_string(
            item.get(
                "priority",
                "MEDIUM"
            )
        ).upper()

        if priority not in [
            "HIGH",
            "MEDIUM",
            "LOW"
        ]:

            priority = "MEDIUM"

        if action:

            cleaned_items.append(
                {
                    "action": action,
                    "priority": priority
                }
            )

    print(
        f"Generated "
        f"{len(cleaned_items)} action items."
    )

    return {
        "action_items": cleaned_items
    }


# ============================================================
# NODE 5
# EVALUATE VIDEO
# ============================================================

def evaluation_node(
    state: AgentState
) -> Dict[str, Any]:

    print()
    print("[5] Evaluating video...")

    summary = state.get(
        "summary",
        {}
    )

    summary_text = json.dumps(
        summary,
        ensure_ascii=False
    )

    system_prompt = """
You are an expert video evaluator.

Evaluate the video based ONLY on the provided summary.

Return ONLY valid JSON.

Use EXACTLY this structure:

{
  "clarity": 0,
  "educational_value": 0,
  "depth": 0,
  "practical_value": 0,
  "engagement": 0,
  "overall_score": 0,
  "strengths": [
    "string",
    "string"
  ],
  "weaknesses": [
    "string",
    "string"
  ],
  "recommendation": "string"
}

Rules:

1. Every score must be between 0 and 10.
2. overall_score must be between 0 and 10.
3. Maximum 2 strengths.
4. Maximum 2 weaknesses.
5. Do not add extra fields.
6. Do not use Markdown.
7. Return valid JSON only.
"""

    user_prompt = f"""
Evaluate this YouTube video summary:

{summary_text}
"""

    try:

        result = call_groq_json(
            system_prompt,
            user_prompt
        )

    except Exception as exc:

        print(
            f"Video evaluation failed: {exc}"
        )

        # Continue with default evaluation
        return {
            "evaluation": {
                "clarity": 0,
                "educational_value": 0,
                "depth": 0,
                "practical_value": 0,
                "engagement": 0,
                "overall_score": 0,
                "strengths": [],
                "weaknesses": [],
                "recommendation":
                    "Evaluation could not be generated."
            },
            "quality_score": 0
        }

    try:

        evaluation = extract_json_result(
            result
        )

    except Exception as exc:

        print(
            f"Evaluation JSON parsing failed: {exc}"
        )

        evaluation = {
            "clarity": 0,
            "educational_value": 0,
            "depth": 0,
            "practical_value": 0,
            "engagement": 0,
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "recommendation":
                "Evaluation could not be generated."
        }

    # ========================================================
    # NORMALIZE SCORES
    # ========================================================

    score_fields = [
        "clarity",
        "educational_value",
        "depth",
        "practical_value",
        "engagement",
        "overall_score"
    ]

    for field in score_fields:

        try:

            value = float(
                evaluation.get(
                    field,
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            value = 0

        # Clamp 0-10
        value = max(
            0,
            min(
                10,
                value
            )
        )

        evaluation[field] = value

    # ========================================================
    # NORMALIZE LISTS
    # ========================================================

    strengths = evaluation.get(
        "strengths",
        []
    )

    weaknesses = evaluation.get(
        "weaknesses",
        []
    )

    if not isinstance(
        strengths,
        list
    ):

        strengths = []

    if not isinstance(
        weaknesses,
        list
    ):

        weaknesses = []

    evaluation["strengths"] = [
        safe_string(x).strip()
        for x in strengths[:2]
        if safe_string(x).strip()
    ]

    evaluation["weaknesses"] = [
        safe_string(x).strip()
        for x in weaknesses[:2]
        if safe_string(x).strip()
    ]

    evaluation["recommendation"] = safe_string(
        evaluation.get(
            "recommendation",
            ""
        )
    ).strip()

    quality_score = float(
        evaluation.get(
            "overall_score",
            0
        )
    )

    print(
        f"Video quality score: "
        f"{quality_score}"
    )

    return {
        "evaluation": evaluation,
        "quality_score": quality_score
    }


# ============================================================
# NODE 6
# GENERATE PDF
# ============================================================

def pdf_node(
    state: AgentState
) -> Dict[str, Any]:

    print()
    print("[6] Generating PDF report...")

    youtube_url = safe_string(
        state.get(
            "youtube_url",
            ""
        )
    )

    summary = state.get(
        "summary",
        {}
    )

    action_items = state.get(
        "action_items",
        []
    )

    evaluation = state.get(
        "evaluation",
        {}
    )

    quality_score = state.get(
        "quality_score",
        0
    )

    # ========================================================
    # IMPORTANT
    #
    # Your pdf_generator.py expects:
    #
    # youtube_url
    # summary
    # action_items
    # evaluation
    # quality_score
    #
    # So pass all five explicitly.
    # ========================================================

    try:

        pdf_path = generate_pdf(

            youtube_url=youtube_url,

            summary=summary,

            action_items=action_items,

            evaluation=evaluation,

            quality_score=quality_score
        )

    except Exception as exc:

        print()
        print(
            "PDF generation failed:"
        )

        print(
            str(exc)
        )

        raise RuntimeError(
            f"PDF generation failed: {exc}"
        )

    if not pdf_path:

        raise RuntimeError(
            "PDF generator did not return a path."
        )

    pdf_path = str(
        pdf_path
    )

    print()
    print(
        "PDF generated successfully:"
    )

    print(
        pdf_path
    )

    return {
        "pdf_path": pdf_path
    }


# ============================================================
# BUILD LANGGRAPH
# ============================================================

def build_graph():

    print()
    print(
        "Building Agentic AI graph..."
    )

    workflow = StateGraph(
        AgentState
    )

    # ========================================================
    # ADD NODES
    # ========================================================

    workflow.add_node(
        "transcript",
        transcript_node
    )

    workflow.add_node(
        "context",
        context_node
    )

    workflow.add_node(
        "summary",
        summary_node
    )

    workflow.add_node(
        "action_items",
        action_items_node
    )

    workflow.add_node(
        "evaluation",
        evaluation_node
    )

    workflow.add_node(
        "pdf",
        pdf_node
    )

    # ========================================================
    # ENTRY POINT
    # ========================================================

    workflow.set_entry_point(
        "transcript"
    )

    # ========================================================
    # EDGES
    # ========================================================

    workflow.add_edge(
        "transcript",
        "context"
    )

    workflow.add_edge(
        "context",
        "summary"
    )

    workflow.add_edge(
        "summary",
        "action_items"
    )

    workflow.add_edge(
        "action_items",
        "evaluation"
    )

    workflow.add_edge(
        "evaluation",
        "pdf"
    )

    workflow.add_edge(
        "pdf",
        END
    )

    # ========================================================
    # COMPILE
    # ========================================================

    graph = workflow.compile()

    print(
        "Agentic AI graph built successfully."
    )

    return graph