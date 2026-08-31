# app/graph.py

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, TypedDict

from dotenv import load_dotenv
from groq import Groq

from app.services.youtube import get_youtube_transcript
from app.services.pdf_generator import generate_pdf


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# ============================================================
# GROQ CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY environment variable is not configured."
    )


client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)


# ============================================================
# IMPORTANT:
# YOUR GROQ LIMIT IS 8000 TPM
#
# Therefore don't send 18,000 characters.
#
# 5,000 characters is much safer.
# ============================================================

MAX_CONTEXT_CHARS = 5000


# ============================================================
# STATE
# ============================================================

class VideoAnalysisState(TypedDict, total=False):

    youtube_url: str

    video_id: str

    transcript: str

    context: str

    summary: Dict[str, Any]

    action_items: List[Dict[str, Any]]

    evaluation: Dict[str, Any]

    pdf_path: str

    error: str


# ============================================================
# LOGGING HELPERS
# ============================================================

def log_separator():
    logger.info("=" * 70)


# ============================================================
# EXTRACT VIDEO ID
# ============================================================

def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID.
    """

    if not url:
        raise ValueError("YouTube URL is empty.")

    patterns = [
        r"(?:youtube\.com/watch\?v=)([^&]+)",
        r"(?:youtu\.be/)([^?&]+)",
        r"(?:youtube\.com/embed/)([^?&]+)",
        r"(?:youtube\.com/shorts/)([^?&]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url
        )

        if match:
            return match.group(1)

    raise ValueError(
        f"Could not extract YouTube video ID from URL: {url}"
    )


# ============================================================
# PREPARE CONTEXT
# ============================================================

def prepare_context(
    transcript: str,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> str:
    """
    Limit transcript size before sending it to Groq.

    IMPORTANT:
    Characters != tokens.

    We keep the context deliberately small because
    your Groq organization currently has an 8000 TPM limit.
    """

    if not transcript:
        raise ValueError(
            "Transcript is empty."
        )

    transcript = transcript.strip()

    logger.info(
        f"Transcript length: {len(transcript)} characters"
    )

    if len(transcript) > max_chars:

        logger.info(
            f"Limiting transcript to {max_chars} characters."
        )

        context = transcript[:max_chars]

    else:

        context = transcript

    logger.info(
        f"Analysis context prepared: {len(context)} characters"
    )

    return context


# ============================================================
# EXTRACT JSON FROM LLM RESPONSE
# ============================================================

def extract_json(text: str) -> Any:
    """
    Robustly extract JSON from an LLM response.

    Handles:

        {...}

    and:

        ```json
        {...}
        ```

    """

    if not text:
        raise ValueError(
            "LLM returned an empty response."
        )

    text = text.strip()

    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.strip()

    # --------------------------------------------------------
    # First attempt: direct JSON
    # --------------------------------------------------------

    try:

        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Find JSON object
    # --------------------------------------------------------

    start_object = text.find("{")
    end_object = text.rfind("}")

    if (
        start_object != -1
        and end_object != -1
        and end_object > start_object
    ):

        candidate = text[
            start_object:end_object + 1
        ]

        try:

            return json.loads(candidate)

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Find JSON array
    # --------------------------------------------------------

    start_array = text.find("[")
    end_array = text.rfind("]")

    if (
        start_array != -1
        and end_array != -1
        and end_array > start_array
    ):

        candidate = text[
            start_array:end_array + 1
        ]

        try:

            return json.loads(candidate)

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Failed
    # --------------------------------------------------------

    logger.error(
        "Invalid Groq JSON:"
    )

    logger.error(
        text
    )

    raise ValueError(
        "Invalid JSON returned by Groq."
    )


# ============================================================
# GROQ CALL
# ============================================================

def call_groq(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1200,
    temperature: float = 0.1,
    retries: int = 2,
) -> str:
    """
    Central Groq API function.

    Handles:

    413 -> reduce input size
    429 -> retry
    other errors -> retry
    """

    last_error = None

    for attempt in range(
        1,
        retries + 1
    ):

        try:

            logger.info(
                f"Groq request (attempt {attempt}/{retries})..."
            )

            response = client.chat.completions.create(

                model=MODEL_NAME,

                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],

                temperature=temperature,

                max_tokens=max_tokens,

            )

            finish_reason = (
                response.choices[0].finish_reason
            )

            logger.info(
                f"Groq finish reason: {finish_reason}"
            )

            result = (
                response
                .choices[0]
                .message
                .content
            )

            if not result:

                raise ValueError(
                    "Groq returned an empty response."
                )

            logger.info(
                "Groq request successful."
            )

            return result.strip()

        except Exception as exc:

            last_error = exc

            error_text = str(exc)

            logger.error(
                f"Groq API error: {error_text}"
            )

            # ------------------------------------------------
            # 413
            # ------------------------------------------------

            if (
                "413" in error_text
                or "Payload Too Large" in error_text
                or "Request too large" in error_text
            ):

                logger.error(
                    "Groq request is too large."
                )

                # Do not waste another identical request.
                raise RuntimeError(
                    "Groq request is too large. "
                    "Reduce transcript context size."
                ) from exc

            # ------------------------------------------------
            # 429
            # ------------------------------------------------

            if (
                "429" in error_text
                or "Too Many Requests" in error_text
                or "rate_limit" in error_text
            ):

                if attempt < retries:

                    wait_seconds = (
                        5 * attempt
                    )

                    logger.info(
                        f"Rate limit reached. "
                        f"Retrying in {wait_seconds} seconds..."
                    )

                    time.sleep(
                        wait_seconds
                    )

                    continue

                raise RuntimeError(
                    "Groq rate limit exceeded. "
                    "Please try again later."
                ) from exc

            # ------------------------------------------------
            # OTHER ERROR
            # ------------------------------------------------

            if attempt < retries:

                wait_seconds = (
                    3 * attempt
                )

                logger.info(
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            raise RuntimeError(
                f"Groq API request failed: {exc}"
            ) from exc

    raise RuntimeError(
        f"Groq API request failed: {last_error}"
    )


# ============================================================
# GROQ JSON CALL
# ============================================================

def call_groq_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1200,
    temperature: float = 0.1,
) -> Any:
    """
    Call Groq and parse JSON safely.
    """

    response = call_groq(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    try:

        return extract_json(
            response
        )

    except Exception as exc:

        logger.error(
            f"JSON parsing failed: {exc}"
        )

        raise RuntimeError(
            f"Invalid JSON returned by Groq: {exc}"
        ) from exc


# ============================================================
# STEP 1
# TRANSCRIPT
# ============================================================

def transcript_node(
    state: VideoAnalysisState,
) -> VideoAnalysisState:

    log_separator()

    logger.info(
        "[1] Extracting YouTube transcript..."
    )

    youtube_url = state["youtube_url"]

    video_id = extract_video_id(
        youtube_url
    )

    logger.info(
        f"Video ID extracted: {video_id}"
    )

    transcript = get_youtube_transcript(
        youtube_url
    )

    if not transcript:

        raise RuntimeError(
            "YouTube transcript could not be retrieved."
        )

    logger.info(
        "TRANSCRIPT RETRIEVED SUCCESSFULLY"
    )

    logger.info(
        f"Transcript length: {len(transcript)} characters"
    )

    return {
        **state,
        "video_id": video_id,
        "transcript": transcript,
    }


# ============================================================
# STEP 2
# PREPARE CONTEXT
# ============================================================

def context_node(
    state: VideoAnalysisState,
) -> VideoAnalysisState:

    log_separator()

    logger.info(
        "[2] Preparing analysis context..."
    )

    transcript = state["transcript"]

    context = prepare_context(
        transcript,
        MAX_CONTEXT_CHARS,
    )

    return {
        **state,
        "context": context,
    }


# ============================================================
# STEP 3
# SUMMARY
# ============================================================

def summary_node(
    state: VideoAnalysisState,
) -> VideoAnalysisState:

    log_separator()

    logger.info(
        "[3] Generating AI summary..."
    )

    context = state["context"]

    system_prompt = """
You are an expert video analysis assistant.

Analyze the provided YouTube transcript.

Return ONLY valid JSON.

Do not use markdown.
Do not use ```json.
Do not add explanations outside JSON.

The JSON must have exactly this structure:

{
  "title": "string",
  "executive_summary": "string",
  "key_takeaways": [
    "string"
  ],
  "important_concepts": [
    "string"
  ],
  "conclusion": "string"
}

Rules:

- key_takeaways must contain 3 to 5 items.
- important_concepts must contain 3 to 5 items.
- Keep the response concise.
- Do not invent information that is not supported by the transcript.
"""

    user_prompt = f"""
Analyze this YouTube transcript:

--- TRANSCRIPT START ---

{context}

--- TRANSCRIPT END ---
"""

    result = call_groq_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=1000,
        temperature=0.1,
    )

    if not isinstance(result, dict):

        raise RuntimeError(
            "Summary response is not a JSON object."
        )

    # --------------------------------------------------------
    # Normalize summary
    # --------------------------------------------------------

    summary = {

        "title": str(
            result.get(
                "title",
                "YouTube Video Analysis"
            )
        ),

        "executive_summary": str(
            result.get(
                "executive_summary",
                ""
            )
        ),

        "key_takeaways": (
            result.get(
                "key_takeaways",
                []
            )
            if isinstance(
                result.get(
                    "key_takeaways",
                    []
                ),
                list
            )
            else []
        ),

        "important_concepts": (
            result.get(
                "important_concepts",
                []
            )
            if isinstance(
                result.get(
                    "important_concepts",
                    []
                ),
                list
            )
            else []
        ),

        "conclusion": str(
            result.get(
                "conclusion",
                ""
            )
        ),
    }

    logger.info(
        "AI summary generated successfully."
    )

    logger.info(
        f"Title: {summary['title']}"
    )

    logger.info(
        f"Key points: "
        f"{len(summary['key_takeaways'])}"
    )

    return {
        **state,
        "summary": summary,
    }


# ============================================================
# STEP 4
# ACTION ITEMS
# ============================================================

def action_items_node(
    state: VideoAnalysisState,
) -> VideoAnalysisState:

    log_separator()

    logger.info(
        "[4] Generating action items..."
    )

    context = state["context"]

    system_prompt = """
You are an AI assistant that extracts practical action items
from a YouTube video transcript.

Return ONLY valid JSON.

Do not use markdown.
Do not use ```json.

Return exactly:

{
  "action_items": [
    {
      "action": "string",
      "priority": "HIGH",
      "reason": "string"
    }
  ]
}

Rules:

- Return 0 to 5 action items.
- Only create action items supported by the transcript.
- Priority must be HIGH, MEDIUM, or LOW.
- Keep each action concise.
"""

    user_prompt = f"""
Extract practical action items from this transcript:

--- TRANSCRIPT START ---

{context}

--- TRANSCRIPT END ---
"""

    result = call_groq_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=700,
        temperature=0.1,
    )

    if isinstance(result, dict):

        action_items = result.get(
            "action_items",
            []
        )

    elif isinstance(result, list):

        action_items = result

    else:

        action_items = []

    if not isinstance(
        action_items,
        list
    ):

        action_items = []

    # --------------------------------------------------------
    # Normalize action items
    # --------------------------------------------------------

    normalized = []

    for item in action_items:

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

        priority = str(
            item.get(
                "priority",
                "MEDIUM"
            )
        ).upper().strip()

        reason = str(
            item.get(
                "reason",
                item.get(
                    "details",
                    ""
                )
            )
        ).strip()

        if priority not in [
            "HIGH",
            "MEDIUM",
            "LOW",
        ]:

            priority = "MEDIUM"

        if action:

            normalized.append(
                {
                    "action": action,
                    "priority": priority,
                    "reason": reason,
                }
            )

    logger.info(
        f"Generated {len(normalized)} action items."
    )

    return {
        **state,
        "action_items": normalized,
    }


# ============================================================
# STEP 5
# EVALUATION
# ============================================================

def evaluation_node(
    state: VideoAnalysisState,
) -> VideoAnalysisState:

    log_separator()

    logger.info(
        "[5] Evaluating video..."
    )

    context = state["context"]

    summary = state.get(
        "summary",
        {}
    )

    action_items = state.get(
        "action_items",
        []
    )

    system_prompt = """
You are an expert evaluator.

Evaluate the quality of the YouTube video analysis.

Return ONLY valid JSON.

Do not use markdown.
Do not use ```json.

Return exactly:

{
  "quality_score": 0,
  "summary_score": 0,
  "action_items_score": 0,
  "feedback": "string"
}

Rules:

- Scores must be numbers between 0 and 10.
- quality_score is the overall analysis quality.
- summary_score evaluates summary quality.
- action_items_score evaluates action-item quality.
- Keep feedback concise.
"""

    # --------------------------------------------------------
    # IMPORTANT:
    # Do not send the entire transcript again.
    #
    # Evaluation can use the generated summary/action items.
    # --------------------------------------------------------

    user_prompt = f"""
Evaluate the following analysis.

SUMMARY:

{json.dumps(summary, ensure_ascii=False)}

ACTION ITEMS:

{json.dumps(action_items, ensure_ascii=False)}

TRANSCRIPT CONTEXT:

{context[:2500]}
"""

    result = call_groq_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=500,
        temperature=0.1,
    )

    if not isinstance(
        result,
        dict
    ):

        result = {}

    # --------------------------------------------------------
    # Normalize scores
    # --------------------------------------------------------

    def normalize_score(
        value,
        default=0.0,
    ):

        try:

            score = float(
                value
            )

            score = max(
                0.0,
                min(
                    10.0,
                    score
                )
            )

            return score

        except (
            TypeError,
            ValueError,
        ):

            return default

    evaluation = {

        "quality_score": normalize_score(
            result.get(
                "quality_score",
                0
            )
        ),

        "summary_score": normalize_score(
            result.get(
                "summary_score",
                0
            )
        ),

        "action_items_score": normalize_score(
            result.get(
                "action_items_score",
                0
            )
        ),

        "feedback": str(
            result.get(
                "feedback",
                ""
            )
        ),
    }

    logger.info(
        f"Video quality score: "
        f"{evaluation['quality_score']}"
    )

    return {
        **state,
        "evaluation": evaluation,
    }


# ============================================================
# STEP 6
# PDF
# ============================================================

def pdf_node(
    state: VideoAnalysisState,
) -> VideoAnalysisState:

    log_separator()

    logger.info(
        "[6] Generating PDF report..."
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

    youtube_url = state.get(
        "youtube_url",
        ""
    )

    try:

        # ====================================================
        # VERY IMPORTANT
        #
        # Your pdf_generator.py expects:
        #
        # generate_pdf(
        #     summary,
        #     action_items,
        #     evaluation,
        #     youtube_url=""
        # )
        #
        # Do NOT pass quality_score separately.
        # ====================================================

        pdf_path = generate_pdf(
            summary=summary,
            action_items=action_items,
            evaluation=evaluation,
            youtube_url=youtube_url,
        )

    except Exception as exc:

        logger.error(
            f"PDF generation failed: {exc}"
        )

        raise RuntimeError(
            f"PDF generation failed: {exc}"
        ) from exc

    if not pdf_path:

        raise RuntimeError(
            "PDF generator returned an empty path."
        )

    logger.info(
        f"PDF generated successfully: {pdf_path}"
    )

    return {
        **state,
        "pdf_path": pdf_path,
    }


# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================

def analyze_video(
    youtube_url: str,
) -> Dict[str, Any]:

    log_separator()

    logger.info(
        "NEW VIDEO ANALYSIS"
    )

    log_separator()

    logger.info(
        f"YouTube URL: {youtube_url}"
    )

    log_separator()

    try:

        # ====================================================
        # INITIAL STATE
        # ====================================================

        state: VideoAnalysisState = {
            "youtube_url": youtube_url,
        }

        logger.info(
            "Building Agentic AI graph..."
        )

        # ====================================================
        # STEP 1
        # ====================================================

        state = transcript_node(
            state
        )

        # ====================================================
        # STEP 2
        # ====================================================

        state = context_node(
            state
        )

        # ====================================================
        # STEP 3
        # ====================================================

        state = summary_node(
            state
        )

        # ====================================================
        # STEP 4
        # ====================================================

        state = action_items_node(
            state
        )

        # ====================================================
        # STEP 5
        # ====================================================

        state = evaluation_node(
            state
        )

        # ====================================================
        # STEP 6
        # ====================================================

        state = pdf_node(
            state
        )

        # ====================================================
        # SUCCESS
        # ====================================================

        log_separator()

        logger.info(
            "VIDEO ANALYSIS COMPLETED SUCCESSFULLY"
        )

        log_separator()

        return {
            "success": True,

            "video_id": state.get(
                "video_id"
            ),

            "youtube_url": state.get(
                "youtube_url"
            ),

            "summary": state.get(
                "summary",
                {}
            ),

            "action_items": state.get(
                "action_items",
                []
            ),

            "evaluation": state.get(
                "evaluation",
                {}
            ),

            "pdf_path": state.get(
                "pdf_path"
            ),
        }

    except Exception as exc:

        log_separator()

        logger.error(
            "ANALYSIS FAILED"
        )

        log_separator()

        logger.error(
            f"Error: {exc}"
        )

        log_separator()

        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# OPTIONAL:
# LANGGRAPH VERSION
# ============================================================

try:

    from langgraph.graph import (
        StateGraph,
        END,
    )

    def build_graph():

        logger.info(
            "Building Agentic AI graph..."
        )

        workflow = StateGraph(
            VideoAnalysisState
        )

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

        # ----------------------------------------------------
        # Flow
        # ----------------------------------------------------

        workflow.set_entry_point(
            "transcript"
        )

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

        graph = workflow.compile()

        logger.info(
            "Agentic AI graph built successfully."
        )

        return graph

except ImportError:

    logger.warning(
        "LangGraph is not installed. "
        "Using sequential execution."
    )

    def build_graph():

        return None


# ============================================================
# GRAPH EXECUTION
# ============================================================

def run_graph(
    youtube_url: str,
) -> Dict[str, Any]:

    graph = build_graph()

    # --------------------------------------------------------
    # If LangGraph exists
    # --------------------------------------------------------

    if graph is not None:

        try:

            result = graph.invoke(
                {
                    "youtube_url": youtube_url
                }
            )

            return {
                "success": True,

                "video_id": result.get(
                    "video_id"
                ),

                "youtube_url": result.get(
                    "youtube_url"
                ),

                "summary": result.get(
                    "summary",
                    {}
                ),

                "action_items": result.get(
                    "action_items",
                    []
                ),

                "evaluation": result.get(
                    "evaluation",
                    {}
                ),

                "pdf_path": result.get(
                    "pdf_path"
                ),
            }

        except Exception as exc:

            logger.error(
                f"Graph execution failed: {exc}"
            )

            return {
                "success": False,
                "error": str(exc),
            }

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return analyze_video(
        youtube_url
    )