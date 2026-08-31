# ============================================================
# graph.py
# YouTube AI Video Analyzer - Agentic AI Graph
# ============================================================

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any, List

from langgraph.graph import StateGraph, END

from app.services.youtube import get_youtube_transcript
from app.services.groq import call_groq_json
from app.services.pdf_generator import generate_pdf


# ============================================================
# STATE
# ============================================================

class VideoState(TypedDict, total=False):

    youtube_url: str

    transcript: Optional[str]

    analysis_context: str

    summary: Dict[str, Any]

    action_items: List[Any]

    evaluation: Dict[str, Any]

    quality_score: float

    pdf_path: str


# ============================================================
# TEXT CLEANER
# ============================================================

def clean_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value)

    # Unicode normalization
    text = unicodedata.normalize(
        "NFKC",
        text
    )

    replacements = {

        # Dashes
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",

        # Bullets
        "\u2022": "-",
        "\u2023": "-",
        "\u2043": "-",

        # Squares
        "\u25A0": "-",
        "\u25AA": "-",
        "\u25AB": "-",
        "\u25FE": "-",
        "\u25FF": "-",

        # Replacement character
        "\uFFFD": "-",

        # Quotes
        "\u2018": "'",
        "\u2019": "'",
        "\u201A": "'",
        "\u201B": "'",

        "\u201C": '"',
        "\u201D": '"',
        "\u201E": '"',
        "\u201F": '"',

        # Ellipsis
        "\u2026": "...",

        # Spaces
        "\u00A0": " ",
        "\u2000": " ",
        "\u2001": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2004": " ",
        "\u2005": " ",
        "\u2006": " ",
        "\u2007": " ",
        "\u2008": " ",
        "\u2009": " ",
        "\u200A": " ",
        "\u202F": " ",
        "\u205F": " ",
        "\u3000": " ",

        # Invisible characters
        "\u200B": "",
        "\u200C": "",
        "\u200D": "",
        "\u2060": "",
        "\uFEFF": "",

        # Soft hyphen
        "\u00AD": "-"
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    # Remove unsupported control characters
    result = []

    for char in text:

        code = ord(char)

        if char in "\n\r\t":

            result.append(char)

        elif code >= 32:

            result.append(char)

    text = "".join(result)

    # Convert remaining unsupported Unicode to ASCII
    text = (
        unicodedata
        .normalize(
            "NFKD",
            text
        )
        .encode(
            "ascii",
            "ignore"
        )
        .decode(
            "ascii"
        )
    )

    # Final safety replacements
    text = text.replace(
        "■",
        "-"
    )

    text = text.replace(
        "□",
        "-"
    )

    text = text.replace(
        "�",
        "-"
    )

    # Whitespace cleanup
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# RECURSIVE CLEANER
# ============================================================

def clean_data(value: Any):

    if isinstance(value, str):

        return clean_text(
            value
        )

    if isinstance(value, dict):

        return {
            key: clean_data(item)
            for key, item in value.items()
        }

    if isinstance(value, list):

        return [
            clean_data(item)
            for item in value
        ]

    return value


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_response(
    response: Any
):

    if response is None:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    # Already dictionary
    if isinstance(
        response,
        dict
    ):

        return clean_data(
            response
        )

    # LangChain-like response
    if hasattr(
        response,
        "content"
    ):

        response = response.content

    text = str(
        response
    ).strip()

    if not text:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    # Remove markdown code fences
    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace(
        "```",
        ""
    ).strip()

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        return clean_data(
            json.loads(text)
        )

    except json.JSONDecodeError:

        pass

    # --------------------------------------------------------
    # Extract JSON object
    # --------------------------------------------------------

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if start == -1 or end == -1:

        raise RuntimeError(
            "AI response did not contain valid JSON."
        )

    json_text = text[
        start:end + 1
    ]

    try:

        return clean_data(
            json.loads(json_text)
        )

    except json.JSONDecodeError as exc:

        print(
            "\nInvalid Groq JSON:"
        )

        print(
            text[:3000]
        )

        raise RuntimeError(
            f"Invalid JSON returned by Groq: {exc}"
        )


# ============================================================
# NODE 1
# EXTRACT YOUTUBE TRANSCRIPT
# ============================================================

def extract_transcript_node(
    state: VideoState
):

    print()
    print(
        "[1] Extracting YouTube transcript..."
    )

    youtube_url = (
        state.get(
            "youtube_url",
            ""
        )
        or ""
    ).strip()

    if not youtube_url:

        raise RuntimeError(
            "YouTube URL is required."
        )

    # --------------------------------------------------------
    # If transcript was already supplied
    # --------------------------------------------------------

    existing_transcript = state.get(
        "transcript"
    )

    if existing_transcript:

        transcript = clean_text(
            existing_transcript
        )

        if transcript:

            print(
                "Transcript already supplied."
            )

            print(
                f"Transcript length: "
                f"{len(transcript)} characters"
            )

            return {
                "transcript": transcript
            }

    # --------------------------------------------------------
    # Use our Supadata-enabled youtube.py
    # --------------------------------------------------------

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
        print(
            "TRANSCRIPT RETRIEVAL FAILED"
        )

        print(
            f"Error: {exc}"
        )

        raise RuntimeError(
            str(exc)
        )

    transcript = clean_text(
        transcript
    )

    if not transcript:

        raise RuntimeError(
            "YouTube transcript is empty."
        )

    print(
        "TRANSCRIPT RETRIEVED SUCCESSFULLY"
    )

    print(
        f"Transcript length: "
        f"{len(transcript)} characters"
    )

    return {
        "transcript": transcript
    }


# ============================================================
# NODE 2
# PREPARE TRANSCRIPT
# ============================================================

def prepare_transcript_node(
    state: VideoState
):

    print()
    print(
        "[2] Preparing analysis context..."
    )

    transcript = clean_text(
        state.get(
            "transcript",
            ""
        )
    )

    if not transcript:

        raise RuntimeError(
            "Transcript is empty."
        )

    print(
        f"Transcript length: "
        f"{len(transcript)} characters"
    )

    # ========================================================
    # IMPORTANT GROQ LIMIT
    # ========================================================
    #
    # Your Groq organization currently has:
    #
    # TPM LIMIT = 8000
    #
    # Previously:
    #
    # 18,000 chars -> approximately 8274 tokens
    #
    # This caused:
    #
    # 413 Payload Too Large
    #
    # Therefore we use a smaller context.
    #
    # 6,000 characters is much safer.
    #
    # ========================================================

    MAX_CHARS = 6000

    if len(transcript) > MAX_CHARS:

        print(
            f"Limiting transcript to "
            f"{MAX_CHARS} characters."
        )

        analysis_context = transcript[
            :MAX_CHARS
        ]

    else:

        analysis_context = transcript

    analysis_context = analysis_context.strip()

    print(
        f"Analysis context prepared: "
        f"{len(analysis_context)} characters"
    )

    return {

        "transcript":
            transcript,

        "analysis_context":
            analysis_context
    }


# ============================================================
# NODE 3
# ANALYZE VIDEO
# ============================================================

def analyze_video_node(
    state: VideoState
):

    print()
    print(
        "[3] Generating AI summary..."
    )

    transcript = clean_text(
        state.get(
            "analysis_context",
            ""
        )
    )

    if not transcript:

        raise RuntimeError(
            "Analysis context is empty."
        )

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    system_prompt = """
You are an expert YouTube video analyst.

Analyze the supplied transcript.

Return ONLY valid JSON.

Do not use Markdown.

Do not use code fences.

Do not add explanations outside JSON.

Use ASCII characters only.

Return exactly this structure:

{
  "title": "string",
  "executive_summary": "string",
  "key_points": [
    "string",
    "string",
    "string"
  ],
  "important_concepts": [
    "string",
    "string"
  ],
  "action_items": [
    {
      "action": "string",
      "priority": "HIGH",
      "reason": "string"
    }
  ],
  "conclusion": "string"
}

Rules:

1. Use only information present in the transcript.
2. Do not invent facts.
3. Keep the executive summary concise.
4. Generate 3 to 5 key points.
5. Generate 2 to 5 important concepts.
6. Generate useful action items when applicable.
7. Priority must be HIGH, MEDIUM, or LOW.
8. Keep the response compact.
9. Return JSON only.
"""

    # ========================================================
    # USER PROMPT
    # ========================================================

    user_prompt = f"""
Analyze this YouTube transcript.

TRANSCRIPT:

{transcript}

Return valid JSON only.
"""

    print()
    print(
        "Calling Groq for video analysis..."
    )

    try:

        response = call_groq_json(

            system_prompt,

            user_prompt,

            # IMPORTANT:
            # Keep output small enough for
            # the 8000 TPM limit.
            max_tokens=1800,

            retries=2
        )

    except Exception as exc:

        print()
        print(
            "SUMMARY GENERATION FAILED"
        )

        print(
            f"Error: {exc}"
        )

        raise RuntimeError(
            f"Summary generation failed: {exc}"
        )

    # ========================================================
    # PARSE RESPONSE
    # ========================================================

    result = parse_json_response(
        response
    )

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Groq analysis did not return a JSON object."
        )

    # ========================================================
    # DEFAULT VALUES
    # ========================================================

    result.setdefault(
        "title",
        "YouTube Video Analysis"
    )

    result.setdefault(
        "executive_summary",
        ""
    )

    result.setdefault(
        "key_points",
        []
    )

    result.setdefault(
        "important_concepts",
        []
    )

    result.setdefault(
        "action_items",
        []
    )

    result.setdefault(
        "conclusion",
        ""
    )

    # ========================================================
    # VALIDATE LISTS
    # ========================================================

    if not isinstance(
        result.get(
            "key_points"
        ),
        list
    ):

        result[
            "key_points"
        ] = []

    if not isinstance(
        result.get(
            "important_concepts"
        ),
        list
    ):

        result[
            "important_concepts"
        ] = []

    if not isinstance(
        result.get(
            "action_items"
        ),
        list
    ):

        result[
            "action_items"
        ] = []

    # ========================================================
    # CLEAN DATA
    # ========================================================

    result = clean_data(
        result
    )

    print()
    print(
        "AI summary generated successfully."
    )

    print(
        f"Title: {result.get('title', '')}"
    )

    print(
        f"Key points: "
        f"{len(result.get('key_points', []))}"
    )

    print(
        f"Action items: "
        f"{len(result.get('action_items', []))}"
    )

    # ========================================================
    # IMPORTANT
    #
    # Action items are already generated by the same
    # analysis request.
    #
    # We do NOT make another Groq call here.
    #
    # This reduces:
    #
    # - TPM usage
    # - API cost
    # - 429 errors
    # - response time
    #
    # ========================================================

    return {

        "summary":
            result,

        "action_items":
            result.get(
                "action_items",
                []
            )
    }


# ============================================================
# NODE 4
# EVALUATE ANALYSIS
# ============================================================

def evaluate_analysis_node(
    state: VideoState
):

    print()
    print(
        "[4] Evaluating video..."
    )

    summary = clean_data(
        state.get(
            "summary",
            {}
        )
    )

    if not summary:

        print(
            "No summary available for evaluation."
        )

        return {

            "evaluation": {
                "accuracy": 0,
                "completeness": 0,
                "clarity": 0,
                "usefulness": 0,
                "overall_score": 0,
                "feedback":
                    "Evaluation could not be generated."
            },

            "quality_score": 0
        }

    # ========================================================
    # EVALUATION PROMPT
    # ========================================================

    system_prompt = """
You are a quality evaluator for YouTube video analysis.

Evaluate the provided analysis.

Return ONLY valid JSON.

Use ASCII characters only.

Return exactly:

{
  "accuracy": 0,
  "completeness": 0,
  "clarity": 0,
  "usefulness": 0,
  "overall_score": 0,
  "feedback": "string"
}

Rules:

1. Scores must be between 0 and 100.
2. Return JSON only.
3. No Markdown.
4. No explanation outside JSON.
5. Keep feedback concise.
"""

    # ========================================================
    # Keep evaluation input small
    # ========================================================

    summary_json = json.dumps(
        summary,
        ensure_ascii=True,
        separators=(
            ",",
            ":"
        )
    )

    user_prompt = (
        "Evaluate this YouTube analysis:\n\n"
        +
        summary_json
    )

    try:

        response = call_groq_json(

            system_prompt,

            user_prompt,

            # Small output to protect TPM
            max_tokens=500,

            retries=2
        )

        evaluation = parse_json_response(
            response
        )

    except Exception as exc:

        print(
            f"Evaluation failed: {exc}"
        )

        # Do not fail entire application
        evaluation = {

            "accuracy": 0,

            "completeness": 0,

            "clarity": 0,

            "usefulness": 0,

            "overall_score": 0,

            "feedback":
                "Evaluation could not be generated."
        }

    evaluation = clean_data(
        evaluation
    )

    # ========================================================
    # Get quality score
    # ========================================================

    score = evaluation.get(
        "overall_score",
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

    # Keep score between 0 and 100
    score = max(
        0,
        min(
            100,
            score
        )
    )

    print(
        f"Video quality score: "
        f"{score}"
    )

    return {

        "evaluation":
            evaluation,

        "quality_score":
            score
    }


# ============================================================
# NODE 5
# GENERATE PDF
# ============================================================

def generate_pdf_node(
    state: VideoState
):

    print()
    print(
        "[5] Generating PDF report..."
    )

    # ========================================================
    # Collect state
    # ========================================================

    youtube_url = clean_text(
        state.get(
            "youtube_url",
            ""
        )
    )

    summary = clean_data(
        state.get(
            "summary",
            {}
        )
    )

    action_items = clean_data(
        state.get(
            "action_items",
            []
        )
    )

    evaluation = clean_data(
        state.get(
            "evaluation",
            {}
        )
    )

    quality_score = state.get(
        "quality_score",
        0
    )

    # ========================================================
    # Final data cleaning
    # ========================================================

    summary = clean_data(
        summary
    )

    action_items = clean_data(
        action_items
    )

    evaluation = clean_data(
        evaluation
    )

    # ========================================================
    # Filename
    # ========================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"youtube_analysis_{timestamp}.pdf"
    )

    # ========================================================
    # Generate PDF
    #
    # IMPORTANT:
    # Your pdf_generator expects:
    #
    # youtube_url
    # summary
    # action_items
    # evaluation
    # quality_score
    # output_filename
    #
    # ========================================================

    try:

        pdf_path = generate_pdf(

            youtube_url=youtube_url,

            summary=summary,

            action_items=action_items,

            evaluation=evaluation,

            quality_score=quality_score,

            output_filename=filename
        )

    except TypeError as exc:

        print()
        print(
            "PDF GENERATOR SIGNATURE ERROR"
        )

        print(
            f"Error: {exc}"
        )

        raise RuntimeError(
            f"PDF generation failed: {exc}"
        )

    except Exception as exc:

        print()
        print(
            "PDF GENERATION FAILED"
        )

        print(
            f"Error: {exc}"
        )

        raise RuntimeError(
            f"PDF generation failed: {exc}"
        )

    # ========================================================
    # Validate PDF path
    # ========================================================

    if not pdf_path:

        raise RuntimeError(
            "PDF generator returned no file path."
        )

    pdf_path = Path(
        pdf_path
    ).resolve()

    if not pdf_path.exists():

        raise RuntimeError(
            f"Generated PDF does not exist: "
            f"{pdf_path}"
        )

    if pdf_path.stat().st_size <= 0:

        raise RuntimeError(
            "Generated PDF is empty."
        )

    print()
    print(
        "PDF GENERATED SUCCESSFULLY"
    )

    print(
        f"PDF path: {pdf_path}"
    )

    print(
        f"PDF size: "
        f"{pdf_path.stat().st_size} bytes"
    )

    return {

        "pdf_path":
            str(pdf_path)
    }


# ============================================================
# BUILD LANGGRAPH
# ============================================================

def build_graph():

    print()
    print(
        "Building Agentic AI graph..."
    )

    # ========================================================
    # Create StateGraph
    # ========================================================

    workflow = StateGraph(
        VideoState
    )

    # ========================================================
    # Add nodes
    # ========================================================

    workflow.add_node(
        "extract_transcript",
        extract_transcript_node
    )

    workflow.add_node(
        "prepare_transcript",
        prepare_transcript_node
    )

    workflow.add_node(
        "analyze_video",
        analyze_video_node
    )

    workflow.add_node(
        "evaluate_analysis",
        evaluate_analysis_node
    )

    workflow.add_node(
        "generate_pdf",
        generate_pdf_node
    )

    # ========================================================
    # Entry point
    # ========================================================

    workflow.set_entry_point(
        "extract_transcript"
    )

    # ========================================================
    # Workflow
    # ========================================================

    workflow.add_edge(
        "extract_transcript",
        "prepare_transcript"
    )

    workflow.add_edge(
        "prepare_transcript",
        "analyze_video"
    )

    workflow.add_edge(
        "analyze_video",
        "evaluate_analysis"
    )

    workflow.add_edge(
        "evaluate_analysis",
        "generate_pdf"
    )

    workflow.add_edge(
        "generate_pdf",
        END
    )

    # ========================================================
    # Compile
    # ========================================================

    graph = workflow.compile()

    print(
        "Agentic AI graph built successfully."
    )

    return graph