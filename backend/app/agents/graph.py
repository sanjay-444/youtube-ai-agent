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


def extract_json_result(result: Any) -> Dict[str, Any]:

    if result is None:
        return {}

    if isinstance(result, dict):
        return result

    if hasattr(result, "content"):

        content = result.content

        if isinstance(content, dict):
            return content

        return {
            "result": content
        }

    return {
        "result": str(result)
    }


# ============================================================
# NODE 1
# GET YOUTUBE TRANSCRIPT
# ============================================================

def transcript_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[1] Extracting YouTube transcript...")

    youtube_url = safe_string(
        state.get("youtube_url")
    ).strip()

    if not youtube_url:

        raise RuntimeError(
            "YouTube URL is required."
        )

    print(
        f"Using transcript function: "
        f"app.services.youtube.get_youtube_transcript"
    )

    try:

        transcript = get_youtube_transcript(
            youtube_url
        )

    except Exception as exc:

        print(
            "Transcript retrieval failed:"
        )

        print(str(exc))

        raise RuntimeError(
            str(exc)
        )

    transcript = safe_string(
        transcript
    )

    if not transcript.strip():

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

    # --------------------------------------------------------
    # IMPORTANT
    #
    # Groq currently has an 8000 TPM limit for your model.
    #
    # Your previous 50000 character context produced:
    #
    # Requested: 15324 tokens
    # Limit:      8000 tokens
    #
    # 18000 characters gives us a much safer request size.
    # --------------------------------------------------------

    max_characters = 10000

    if len(transcript) > max_characters:

        print(
            f"Limiting transcript to "
            f"{max_characters} characters."
        )

        transcript = transcript[
            :max_characters
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

    print("[3] Generating AI summary...")

    context = safe_string(
        state.get("analysis_context")
    ).strip()

    if not context:

        raise RuntimeError(
            "Analysis context is empty."
        )

    system_prompt = """
You are an expert YouTube video analyst.

Analyze the provided transcript carefully.

Return ONLY valid JSON.

Do not use Markdown.
Do not add explanations outside JSON.

Use this structure:

{
    "title": "Best inferred title",
    "overview": "Short overview of the video",
    "summary": "Detailed but concise summary",
    "key_points": [
        "Key point 1",
        "Key point 2",
        "Key point 3"
    ],
    "topics": [
        "Topic 1",
        "Topic 2"
    ],
    "conclusion": "Main conclusion of the video"
}
"""

    user_prompt = f"""
Analyze the following YouTube transcript.

TRANSCRIPT:

{context}
"""

    try:

        result = call_groq_json(
            system_prompt,
            user_prompt
        )

    except Exception as exc:

        print(
            f"Summary generation failed: {exc}"
        )

        raise RuntimeError(
            f"Summary generation failed: {exc}"
        )

    summary = extract_json_result(
        result
    )

    if not summary:

        raise RuntimeError(
            "Groq returned an empty summary."
        )

    print(
        "AI summary generated successfully."
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

    print("[4] Generating action items...")

    context = safe_string(
        state.get("analysis_context")
    ).strip()

    summary = state.get(
        "summary",
        {}
    )

    system_prompt = """
You are an expert YouTube content analyst.

Identify practical and useful action items
from the video.

Return ONLY valid JSON.

Use this structure:

{
    "action_items": [
        {
            "action": "Action to take",
            "reason": "Why this action is useful",
            "priority": "High"
        }
    ]
}

Priority must be one of:

High
Medium
Low
"""

    user_prompt = f"""
Based on the following video analysis and transcript,
identify the most useful practical action items.

VIDEO SUMMARY:

{summary}

TRANSCRIPT:

{context}
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

        raise RuntimeError(
            f"Action item generation failed: {exc}"
        )

    parsed = extract_json_result(
        result
    )

    action_items = parsed.get(
        "action_items",
        []
    )

    if not isinstance(
        action_items,
        list
    ):

        action_items = []

    print(
        f"Generated {len(action_items)} action items."
    )

    return {
        "action_items": action_items
    }


# ============================================================
# NODE 5
# EVALUATE VIDEO
# ============================================================

def evaluation_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[5] Evaluating video...")

    context = safe_string(
        state.get("analysis_context")
    ).strip()

    summary = state.get(
        "summary",
        {}
    )

    system_prompt = """
You are an expert video-content evaluator.

Evaluate the quality of the provided video content.

Return ONLY valid JSON.

Use this structure:

{
    "clarity": 0,
    "educational_value": 0,
    "depth": 0,
    "practical_value": 0,
    "engagement": 0,
    "overall_score": 0,
    "strengths": [
        "Strength 1",
        "Strength 2"
    ],
    "weaknesses": [
        "Weakness 1",
        "Weakness 2"
    ],
    "recommendation": "Recommendation"
}

All scores must be between 0 and 10.
"""

    user_prompt = f"""
Evaluate this YouTube video.

VIDEO SUMMARY:

{summary}

TRANSCRIPT:

{context}
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

        raise RuntimeError(
            f"Video evaluation failed: {exc}"
        )

    evaluation = extract_json_result(
        result
    )

    if not evaluation:

        evaluation = {
            "overall_score": 0
        }

    quality_score = evaluation.get(
        "overall_score",
        0
    )

    try:

        quality_score = float(
            quality_score
        )

    except (
        TypeError,
        ValueError
    ):

        quality_score = 0

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

    print("[6] Generating PDF report...")

    youtube_url = safe_string(
        state.get("youtube_url")
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

    try:

        pdf_path = generate_pdf(
            youtube_url=youtube_url,
            summary=summary,
            action_items=action_items,
            evaluation=evaluation,
            quality_score=quality_score
        )

    except TypeError:

        # ----------------------------------------------------
        # Compatibility fallback
        #
        # If your existing pdf_generator.py uses a different
        # function signature, try passing the complete state.
        # ----------------------------------------------------

        try:

            pdf_path = generate_pdf(
                state
            )

        except Exception as exc:

            print(
                f"PDF generation failed: {exc}"
            )

            raise RuntimeError(
                f"PDF generation failed: {exc}"
            )

    except Exception as exc:

        print(
            f"PDF generation failed: {exc}"
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

    print(
        f"PDF generated successfully: "
        f"{pdf_path}"
    )

    return {
        "pdf_path": pdf_path
    }


# ============================================================
# BUILD LANGGRAPH
# ============================================================

def build_graph():

    print(
        "Building Agentic AI graph..."
    )

    workflow = StateGraph(
        AgentState
    )

    # --------------------------------------------------------
    # Add nodes
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Entry point
    # --------------------------------------------------------

    workflow.set_entry_point(
        "transcript"
    )

    # --------------------------------------------------------
    # Workflow edges
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Compile graph
    # --------------------------------------------------------

    graph = workflow.compile()

    print(
        "Agentic AI graph built successfully."
    )

    return graph