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

        # Black squares / boxes
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
        "\u00AD": "-",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    # Remove control characters
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
        .normalize("NFKD", text)
        .encode(
            "ascii",
            "ignore"
        )
        .decode(
            "ascii"
        )
    )

    # Final safety replacements
    text = text.replace("■", "-")
    text = text.replace("□", "-")
    text = text.replace("�", "-")

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

    if isinstance(
        value,
        str
    ):

        return clean_text(
            value
        )

    if isinstance(
        value,
        dict
    ):

        return {

            key: clean_data(
                item
            )

            for key, item in value.items()
        }

    if isinstance(
        value,
        list
    ):

        return [

            clean_data(
                item
            )

            for item in value
        ]

    return value


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_response(response: Any):

    if response is None:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    if isinstance(
        response,
        dict
    ):

        return clean_data(
            response
        )

    text = str(
        response
    ).strip()

    if not text:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    # Remove markdown fences
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

    # Direct JSON
    try:

        return clean_data(
            json.loads(text)
        )

    except json.JSONDecodeError:

        pass

    # Extract JSON object
    start = text.find("{")
    end = text.rfind("}")

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
            text[:5000]
        )

        raise RuntimeError(
            f"Invalid JSON returned by Groq: {exc}"
        )


# ============================================================
# TRANSCRIPT EXTRACTION
# ============================================================

def extract_transcript_node(
    state: VideoState
):

    print(
        "\n[1] Extracting YouTube transcript..."
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
    # IMPORTANT
    #
    # If main.py already supplied transcript, use it.
    # --------------------------------------------------------

    existing_transcript = state.get(
        "transcript"
    )

    if existing_transcript:

        transcript = clean_text(
            existing_transcript
        )

        print(
            f"Transcript already supplied."
        )

        print(
            f"Transcript length: "
            f"{len(transcript)} characters"
        )

        return {

            "transcript":
                transcript
        }

    # --------------------------------------------------------
    # Import the EXISTING transcript implementation.
    #
    # Your earlier project already had transcript extraction
    # working. We try the common module/function combinations
    # instead of requiring a new transcript.py.
    # --------------------------------------------------------

    transcript = None
    last_error = None

    candidates = [

        (
            "app.services.youtube",
            "get_transcript"
        ),

        (
            "app.services.youtube",
            "get_youtube_transcript"
        ),

        (
            "app.services.youtube_transcript",
            "get_transcript"
        ),

        (
            "app.services.youtube_transcript",
            "get_youtube_transcript"
        ),

        (
            "app.utils.youtube",
            "get_transcript"
        ),

        (
            "app.utils.youtube",
            "get_youtube_transcript"
        ),

    ]

    for module_name, function_name in candidates:

        try:

            module = __import__(
                module_name,
                fromlist=[function_name]
            )

            function = getattr(
                module,
                function_name,
                None
            )

            if function is None:
                continue

            print(
                f"Using transcript function: "
                f"{module_name}.{function_name}"
            )

            transcript = function(
                youtube_url
            )

            if transcript:
                break

        except Exception as exc:

            last_error = exc

            continue

    # --------------------------------------------------------
    # If no function was found
    # --------------------------------------------------------

    if not transcript:

        message = (
            "Could not find the existing YouTube transcript "
            "function in your project."
        )

        if last_error:

            message += (
                f" Last error: {last_error}"
            )

        raise RuntimeError(
            message
        )

    # --------------------------------------------------------
    # Clean transcript
    # --------------------------------------------------------

    transcript = clean_text(
        transcript
    )

    if not transcript:

        raise RuntimeError(
            "YouTube transcript is empty."
        )

    print(
        f"Transcript retrieved successfully."
    )

    print(
        f"Transcript length: "
        f"{len(transcript)} characters"
    )

    return {

        "transcript":
            transcript
    }


# ============================================================
# PREPARE TRANSCRIPT
# ============================================================

def prepare_transcript_node(
    state: VideoState
):

    print(
        "\n[2] Preparing transcript..."
    )

    transcript = state.get(
        "transcript",
        ""
    )

    transcript = clean_text(
        transcript
    )

    if not transcript:

        raise RuntimeError(
            "Transcript is empty."
        )

    print(
        f"[2] Transcript size: "
        f"{len(transcript)} characters"
    )

    # --------------------------------------------------------
    # Limit prompt size
    # --------------------------------------------------------

    MAX_CHARS = 18000

    if len(transcript) > MAX_CHARS:

        analysis_context = transcript[
            :MAX_CHARS
        ]

        print(
            f"[2] Analysis transcript length: "
            f"{len(analysis_context)} characters"
        )

        print(
            "[2] Transcript truncated for analysis."
        )

    else:

        analysis_context = transcript

        print(
            f"[2] Analysis transcript length: "
            f"{len(analysis_context)} characters"
        )

    return {

        "transcript":
            transcript,

        "analysis_context":
            analysis_context
    }


# ============================================================
# ANALYZE VIDEO
# ============================================================

def analyze_video_node(
    state: VideoState
):

    print(
        "\n[3] Running Video Analysis Agent..."
    )

    transcript = state.get(
        "analysis_context",
        ""
    )

    if not transcript:

        raise RuntimeError(
            "Analysis context is empty."
        )

    system_prompt = """
You are an expert YouTube video analysis assistant.

Analyze the transcript and return ONLY valid JSON.

IMPORTANT:
Use ASCII characters only.

Do not use:
- Unicode bullets
- en dash
- em dash
- special quotation marks
- black square symbols
- unsupported Unicode symbols

Use normal ASCII "-" when a dash is needed.

Return EXACTLY this structure:

{
  "title": "string",
  "executive_summary": "string",
  "key_points": [
    "string"
  ],
  "important_concepts": [
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

- Return JSON only.
- No markdown.
- No ```json.
- Do not add text before or after JSON.
- Do not invent information.
- Base the answer only on the transcript.
"""

    user_prompt = f"""
Analyze the following YouTube transcript.

TRANSCRIPT:

{transcript}

Return valid JSON only.
"""

    print(
        "\nCalling Groq..."
    )

    response = call_groq_json(
        system_prompt,
        user_prompt,
        max_tokens=5000,
        retries=2
    )

    result = parse_json_response(
        response
    )

    # --------------------------------------------------------
    # Ensure expected fields exist
    # --------------------------------------------------------

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

    result = clean_data(
        result
    )

    print(
        "\n[3] Video analysis completed."
    )

    print(
        f"Title: {result.get('title', '')}"
    )

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
# EVALUATE
# ============================================================

def evaluate_analysis_node(
    state: VideoState
):

    print(
        "\n[4] Evaluating analysis..."
    )

    summary = clean_data(
        state.get(
            "summary",
            {}
        )
    )

    system_prompt = """
You are a quality evaluator.

Evaluate the provided YouTube video analysis.

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

All scores must be between 0 and 100.

No markdown.
No explanations outside JSON.
"""

    user_prompt = (
        "Evaluate this analysis:\n\n"
        +
        json.dumps(
            summary,
            ensure_ascii=True,
            indent=2
        )
    )

    try:

        response = call_groq_json(
            system_prompt,
            user_prompt,
            max_tokens=1000,
            retries=2
        )

        evaluation = parse_json_response(
            response
        )

    except Exception as exc:

        print(
            f"[4] Evaluation failed: {exc}"
        )

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

    score = evaluation.get(
        "overall_score",
        0
    )

    try:

        score = float(
            score
        )

    except Exception:

        score = 0

    print(
        f"[4] Quality score: {score}"
    )

    return {

        "evaluation":
            evaluation,

        "quality_score":
            score
    }


# ============================================================
# GENERATE PDF
# ============================================================

def generate_pdf_node(
    state: VideoState
):

    print(
        "\n[5] Generating PDF..."
    )

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

    # --------------------------------------------------------
    # Final black-box removal
    # --------------------------------------------------------

    def remove_boxes(value):

        if isinstance(
            value,
            str
        ):

            return (
                value
                .replace("■", "-")
                .replace("□", "-")
                .replace("�", "-")
            )

        if isinstance(
            value,
            dict
        ):

            return {

                key: remove_boxes(
                    item
                )

                for key, item in value.items()
            }

        if isinstance(
            value,
            list
        ):

            return [

                remove_boxes(
                    item
                )

                for item in value
            ]

        return value

    summary = remove_boxes(
        summary
    )

    action_items = remove_boxes(
        action_items
    )

    evaluation = remove_boxes(
        evaluation
    )

    print(
        "Final PDF data cleaned."
    )

    # --------------------------------------------------------
    # Filename
    # --------------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"youtube_analysis_{timestamp}.pdf"
    )

    # --------------------------------------------------------
    # Call PDF generator
    # --------------------------------------------------------

    pdf_path = generate_pdf(
        youtube_url=youtube_url,
        summary=summary,
        action_items=action_items,
        evaluation=evaluation,
        quality_score=quality_score,
        output_filename=filename
    )

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

    if pdf_path.stat().st_size == 0:

        raise RuntimeError(
            "Generated PDF is empty."
        )

    print(
        f"[5] PDF generated successfully:"
    )

    print(
        pdf_path
    )

    return {

        "pdf_path":
            str(pdf_path)
    }


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph():

    print(
        "\nBuilding Agentic AI graph..."
    )

    workflow = StateGraph(
        VideoState
    )

    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Entry
    # --------------------------------------------------------

    workflow.set_entry_point(
        "extract_transcript"
    )

    # --------------------------------------------------------
    # Edges
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Compile
    # --------------------------------------------------------

    graph = workflow.compile()

    print(
        "Agentic AI graph built successfully."
    )

    return graph