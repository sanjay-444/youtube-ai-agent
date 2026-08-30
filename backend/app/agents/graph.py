# ============================================================
# backend/app/agents/graph.py
# ============================================================

from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END

from app.services.youtube import get_youtube_transcript
from app.services.groq import call_groq_json
from app.services.pdf_generator import generate_pdf


# ============================================================
# AGENT STATE
# ============================================================

class AgentState(TypedDict, total=False):

    youtube_url: str

    transcript: str | None

    analysis_context: str

    summary: Dict[str, Any]

    action_items: List[Any]

    evaluation: Dict[str, Any]

    quality_score: float

    pdf_path: str


# ============================================================
# HELPER FUNCTION
# ============================================================

def safe_string(value: Any) -> str:
    """
    Safely convert a value to string.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    return str(value)


# ============================================================
# 1. TRANSCRIPT NODE
# ============================================================

def transcript_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[1] Extracting YouTube transcript...")

    youtube_url = state.get(
        "youtube_url",
        ""
    )

    if not youtube_url:

        raise RuntimeError(
            "YouTube URL is missing."
        )

    print(
        "Using transcript function: "
        "app.services.youtube.get_youtube_transcript"
    )

    # IMPORTANT:
    # Directly call youtube.py.
    #
    # There is NO app.utils fallback here.
    # This prevents the previous:
    #
    # No module named 'app.utils'
    #
    # error.

    transcript = get_youtube_transcript(
        youtube_url
    )

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
# 2. CONTEXT NODE
# ============================================================

def context_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[2] Preparing analysis context...")

    transcript = state.get(
        "transcript",
        ""
    )

    transcript = safe_string(
        transcript
    )

    if not transcript:

        raise RuntimeError(
            "Transcript is unavailable."
        )

    # --------------------------------------------------------
    # Prevent extremely large LLM requests
    # --------------------------------------------------------

    max_characters = 50000

    if len(transcript) > max_characters:

        print(
            f"Transcript length: "
            f"{len(transcript)} characters"
        )

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
# 3. SUMMARY NODE
# ============================================================

def summary_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[3] Generating AI summary...")

    context = state.get(
        "analysis_context",
        ""
    )

    if not context:

        raise RuntimeError(
            "Analysis context is empty."
        )

    prompt = f"""
You are an expert YouTube video analyst.

Analyze the following YouTube video transcript.

Create a clear and useful structured summary.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "title": "Suitable title for the video",
    "overview": "Concise overview of the video",
    "key_points": [
        "Important point 1",
        "Important point 2",
        "Important point 3"
    ],
    "main_topics": [
        "Topic 1",
        "Topic 2",
        "Topic 3"
    ],
    "conclusion": "Main conclusion of the video"
}}

Do not include markdown.
Do not include ```json.
Return only JSON.

TRANSCRIPT:

{context}
"""

    result = call_groq_json(
         "You are an expert YouTube video analyst. Return only valid JSON.",
        prompt
    )

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Groq summary response "
            "is not a JSON object."
        )

    print(
        "AI summary generated successfully."
    )

    return {
        "summary": result
    }


# ============================================================
# 4. ACTION ITEMS NODE
# ============================================================

def action_items_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[4] Extracting action items...")

    context = state.get(
        "analysis_context",
        ""
    )

    summary = state.get(
        "summary",
        {}
    )

    prompt = f"""
You are an expert video analyst.

Analyze the video summary and transcript.

Identify useful:

- actions
- recommendations
- practical takeaways
- lessons
- things the viewer can implement

Return ONLY valid JSON.

Use exactly this structure:

{{
    "action_items": [
        {{
            "action": "Specific action",
            "reason": "Why this action is useful"
        }}
    ]
}}

If there are no meaningful action items,
return:

{{
    "action_items": []
}}

Do not include markdown.
Do not include ```json.

SUMMARY:

{summary}

TRANSCRIPT:

{context}
"""

    result = call_groq_json(
        "You are an expert video analyst. Return only valid JSON.",
        prompt
    )

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Groq action-items response "
            "is not a JSON object."
        )

    action_items = result.get(
        "action_items",
        []
    )

    if not isinstance(
        action_items,
        list
    ):

        action_items = []

    print(
        f"Action items extracted: "
        f"{len(action_items)}"
    )

    return {
        "action_items": action_items
    }


# ============================================================
# 5. EVALUATION NODE
# ============================================================

def evaluation_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[5] Evaluating video quality...")

    context = state.get(
        "analysis_context",
        ""
    )

    summary = state.get(
        "summary",
        {}
    )

    action_items = state.get(
        "action_items",
        []
    )

    prompt = f"""
You are an expert content evaluator.

Evaluate the quality and usefulness of this
YouTube video based ONLY on the supplied content.

Evaluate:

1. Overall quality
2. Strengths
3. Weaknesses
4. Educational value
5. Practical value
6. Overall quality score

Return ONLY valid JSON.

Use exactly this structure:

{{
    "overall_assessment": "Short overall assessment",
    "strengths": [
        "Strength 1",
        "Strength 2"
    ],
    "weaknesses": [
        "Weakness 1",
        "Weakness 2"
    ],
    "educational_value": "Low",
    "practical_value": "Medium",
    "quality_score": 75
}}

quality_score must be a number from 0 to 100.

educational_value must be one of:

Low
Medium
High

practical_value must be one of:

Low
Medium
High

Do not include markdown.
Do not include ```json.

SUMMARY:

{summary}

ACTION ITEMS:

{action_items}

TRANSCRIPT:

{context}
"""

    result = call_groq_json(
        "You are an expert video analyst. Return only valid JSON.",
        prompt
    )

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Groq evaluation response "
            "is not a JSON object."
        )

    # --------------------------------------------------------
    # Get quality score
    # --------------------------------------------------------

    score = result.get(
        "quality_score",
        0
    )

    try:

        score = float(
            score
        )

    except (
        TypeError,
        ValueError
    ):

        score = 0

    # --------------------------------------------------------
    # Keep score between 0 and 100
    # --------------------------------------------------------

    score = max(
        0,
        min(
            100,
            score
        )
    )

    result["quality_score"] = score

    print(
        f"Quality score: {score}"
    )

    return {
        "evaluation": result,
        "quality_score": score
    }


# ============================================================
# 6. PDF NODE
# ============================================================

def pdf_node(
    state: AgentState
) -> Dict[str, Any]:

    print("[6] Generating PDF report...")

    youtube_url = state.get(
        "youtube_url",
        ""
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

    # --------------------------------------------------------
    # Generate PDF
    # --------------------------------------------------------

    pdf_path = generate_pdf(
        youtube_url=youtube_url,
        summary=summary,
        action_items=action_items,
        evaluation=evaluation,
        quality_score=quality_score
    )

    if not pdf_path:

        raise RuntimeError(
            "PDF generator did not return a PDF path."
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

    # --------------------------------------------------------
    # Create StateGraph
    # --------------------------------------------------------

    workflow = StateGraph(
        AgentState
    )

    # --------------------------------------------------------
    # Add Nodes
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
    # START
    # --------------------------------------------------------

    workflow.add_edge(
        START,
        "transcript"
    )

    # --------------------------------------------------------
    # Transcript → Context
    # --------------------------------------------------------

    workflow.add_edge(
        "transcript",
        "context"
    )

    # --------------------------------------------------------
    # Context → Summary
    # --------------------------------------------------------

    workflow.add_edge(
        "context",
        "summary"
    )

    # --------------------------------------------------------
    # Summary → Action Items
    # --------------------------------------------------------

    workflow.add_edge(
        "summary",
        "action_items"
    )

    # --------------------------------------------------------
    # Action Items → Evaluation
    # --------------------------------------------------------

    workflow.add_edge(
        "action_items",
        "evaluation"
    )

    # --------------------------------------------------------
    # Evaluation → PDF
    # --------------------------------------------------------

    workflow.add_edge(
        "evaluation",
        "pdf"
    )

    # --------------------------------------------------------
    # PDF → END
    # --------------------------------------------------------

    workflow.add_edge(
        "pdf",
        END
    )

    # --------------------------------------------------------
    # Compile Graph
    # --------------------------------------------------------

    graph = workflow.compile()

    print(
        "Agentic AI graph built successfully."
    )

    return graph