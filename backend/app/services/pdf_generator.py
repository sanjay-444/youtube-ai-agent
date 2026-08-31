import os
import re
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


# ============================================================
# VERCEL-SAFE OUTPUT DIRECTORY
# ============================================================
#
# Vercel's deployed filesystem is read-only except for /tmp.
#
# Therefore we generate the PDF inside the system temporary
# directory.
#
# IMPORTANT:
# The PDF should be returned/downloaded immediately because
# files in /tmp are temporary.
#
# ============================================================

OUTPUT_DIR = (
    Path(tempfile.gettempdir())
    / "youtube_ai_agent"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """
    Convert any value into clean text.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


# ============================================================
# PDF SAFE TEXT
# ============================================================

def pdf_safe(value):
    """
    Convert AI-generated text into PDF-safe ASCII text.

    ReportLab's default Helvetica font does not support every
    Unicode character.

    Unsupported Unicode characters can appear as black boxes
    in the generated PDF.

    This function converts common Unicode characters into
    ASCII equivalents.
    """

    text = clean_text(value)

    if not text:
        return ""

    # --------------------------------------------------------
    # Remove null characters
    # --------------------------------------------------------

    text = text.replace("\x00", "")

    # --------------------------------------------------------
    # Unicode replacements
    # --------------------------------------------------------

    replacements = {

        # ====================================================
        # SMART SINGLE QUOTES
        # ====================================================

        "\u2018": "'",       # Left single quotation mark
        "\u2019": "'",       # Right single quotation mark
        "\u201a": "'",       # Single low-9 quotation mark
        "\u201b": "'",       # Single high-reversed-9 quotation

        # ====================================================
        # SMART DOUBLE QUOTES
        # ====================================================

        "\u201c": '"',       # Left double quotation mark
        "\u201d": '"',       # Right double quotation mark
        "\u201e": '"',       # Double low-9 quotation mark
        "\u201f": '"',       # Double high-reversed-9 quotation

        # ====================================================
        # HYPHENS / DASHES
        # ====================================================

        "\u2010": "-",       # Hyphen
        "\u2011": "-",       # Non-breaking hyphen
        "\u2012": "-",       # Figure dash
        "\u2013": "-",       # En dash
        "\u2014": "-",       # Em dash
        "\u2015": "-",       # Horizontal bar
        "\u2043": "-",       # Hyphen bullet
        "\u2212": "-",       # Mathematical minus

        # ====================================================
        # SPACES
        # ====================================================

        "\u00a0": " ",       # Non-breaking space
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
        "\u200a": " ",
        "\u202f": " ",
        "\u205f": " ",

        # ====================================================
        # ZERO-WIDTH CHARACTERS
        # ====================================================

        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\u2060": "",
        "\ufeff": "",

        # ====================================================
        # ELLIPSIS
        # ====================================================

        "\u2026": "...",

        # ====================================================
        # BULLETS
        # ====================================================

        "\u2022": "-",
        "\u2023": "-",
        "\u25e6": "-",
        "\u2043": "-",

        # ====================================================
        # ARROWS
        # ====================================================

        "\u2190": "<-",
        "\u2191": "^",
        "\u2192": "->",
        "\u2193": "v",
        "\u2194": "<->",
        "\u21d2": "=>",
        "\u21d0": "<=",
        "\u21d4": "<=>",

        # ====================================================
        # MIDDLE DOTS
        # ====================================================

        "\u00b7": "-",
        "\u2027": "-",

        # ====================================================
        # CHECK MARKS
        # ====================================================

        "\u2713": "OK",
        "\u2714": "OK",
        "\u2611": "OK",

        # ====================================================
        # CROSS MARKS
        # ====================================================

        "\u2717": "X",
        "\u2718": "X",
        "\u2612": "X",

        # ====================================================
        # WARNING SYMBOL
        # ====================================================

        "\u26a0": "Warning",

        # ====================================================
        # REGISTERED / COPYRIGHT / TRADEMARK
        # ====================================================

        "\u00ae": "(R)",
        "\u00a9": "(C)",
        "\u2122": "(TM)",

        # ====================================================
        # MATHEMATICAL SYMBOLS
        # ====================================================

        "\u00d7": "x",
        "\u00f7": "/",
        "\u2248": "~",
        "\u2260": "!=",
        "\u2264": "<=",
        "\u2265": ">=",

        # ====================================================
        # FRACTIONS
        # ====================================================

        "\u00bc": "1/4",
        "\u00bd": "1/2",
        "\u00be": "3/4",

        # ====================================================
        # DEGREE
        # ====================================================

        "\u00b0": " degrees ",

        # ====================================================
        # PRIME SYMBOLS
        # ====================================================

        "\u2032": "'",
        "\u2033": '"',

        # ====================================================
        # PER MILLE
        # ====================================================

        "\u2030": "%",

        # ====================================================
        # FULL-WIDTH CHARACTERS
        # ====================================================

        "\uff0d": "-",
        "\uff1a": ":",
        "\uff1b": ";",
        "\uff0c": ",",
        "\uff01": "!",
        "\uff1f": "?",
    }

    # --------------------------------------------------------
    # Apply replacements
    # --------------------------------------------------------

    for old, new in replacements.items():
        text = text.replace(old, new)

    # --------------------------------------------------------
    # Normalize Unicode
    # --------------------------------------------------------

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    # --------------------------------------------------------
    # Convert remaining unsupported Unicode characters
    # into ASCII.
    #
    # This is the final protection against black boxes.
    # --------------------------------------------------------

    text = (
        text
        .encode("ascii", "replace")
        .decode("ascii")
    )

    return text.strip()


# ============================================================
# ESCAPE REPORTLAB XML
# ============================================================

def escape_xml(value):
    """
    Escape text before passing it to ReportLab Paragraph.

    ReportLab Paragraph interprets text as XML/HTML.
    Therefore &, < and > must be escaped.
    """

    text = pdf_safe(value)

    if not text:
        return ""

    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return text


# ============================================================
# SAFE FILENAME
# ============================================================

def safe_filename(text):
    """
    Create a filesystem-safe filename.
    """

    text = clean_text(text)

    if not text:
        text = "youtube_analysis"

    text = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        text
    )

    return text[:80]


# ============================================================
# NORMALIZE LIST
# ============================================================

def normalize_list(value):
    """
    Make sure a value is returned as a list.
    """

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


# ============================================================
# GET ACTION ITEM VALUE
# ============================================================

def get_action_value(item, key, default=""):
    """
    Safely extract a field from an action item.
    """

    if isinstance(item, dict):
        return item.get(key, default)

    return default


# ============================================================
# GENERATE PDF
# ============================================================

def generate_pdf(
    summary,
    action_items,
    evaluation,
    youtube_url="",
    output_dir=None,
):
    """
    Generate a PDF report from the AI video analysis.

    Parameters
    ----------
    summary : dict
        Expected fields:

        title
        executive_summary
        key_takeaways
        important_concepts
        conclusion

    action_items : list
        Expected fields:

        action
        priority
        reason
        details

    evaluation : dict
        Expected fields:

        quality_score
        summary_score
        action_items_score
        feedback

    youtube_url : str
        Original YouTube URL.

    output_dir : str or Path, optional
        Custom output directory.

        If omitted, /tmp/youtube_ai_agent is used.

    Returns
    -------
    str
        Absolute path of generated PDF.
    """

    # ========================================================
    # LOG
    # ========================================================

    print(
        "[PDF] Starting PDF generation..."
    )

    # ========================================================
    # OUTPUT DIRECTORY
    # ========================================================

    if output_dir is None:

        output_path = OUTPUT_DIR

    else:

        output_path = Path(output_dir)

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # NORMALIZE INPUTS
    # ========================================================

    if not isinstance(summary, dict):
        summary = {}

    if not isinstance(action_items, list):
        action_items = []

    if not isinstance(evaluation, dict):
        evaluation = {}

    # ========================================================
    # FILE NAME
    # ========================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    filename = (
        f"youtube_analysis_{timestamp}.pdf"
    )

    pdf_path = (
        output_path / filename
    )

    # ========================================================
    # DOCUMENT
    # ========================================================

    document = SimpleDocTemplate(

        str(pdf_path),

        pagesize=A4,

        rightMargin=45,
        leftMargin=45,

        topMargin=45,
        bottomMargin=45,

        title="YouTube AI Video Analysis",

        author="YouTube AI Video Analyzer",

        subject="AI generated YouTube video analysis",
    )

    # ========================================================
    # STYLES
    # ========================================================

    styles = getSampleStyleSheet()

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title_style = ParagraphStyle(

        "ReportTitle",

        parent=styles["Title"],

        alignment=TA_CENTER,

        fontName="Helvetica-Bold",

        fontSize=22,

        leading=28,

        spaceAfter=15,
    )

    # --------------------------------------------------------
    # Main Heading
    # --------------------------------------------------------

    heading_style = ParagraphStyle(

        "ReportHeading",

        parent=styles["Heading2"],

        fontName="Helvetica-Bold",

        fontSize=15,

        leading=19,

        spaceBefore=12,

        spaceAfter=8,
    )

    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

    body_style = ParagraphStyle(

        "ReportBody",

        parent=styles["BodyText"],

        fontName="Helvetica",

        fontSize=10.5,

        leading=16,

        spaceAfter=8,
    )

    # --------------------------------------------------------
    # Small
    # --------------------------------------------------------

    small_style = ParagraphStyle(

        "ReportSmall",

        parent=styles["BodyText"],

        fontName="Helvetica",

        fontSize=8.5,

        leading=12,

        spaceAfter=4,
    )

    # --------------------------------------------------------
    # Table Header
    # --------------------------------------------------------

    table_header_style = ParagraphStyle(

        "TableHeader",

        parent=styles["BodyText"],

        fontName="Helvetica-Bold",

        fontSize=8.5,

        leading=11,
    )

    # ========================================================
    # STORY
    # ========================================================

    story = []

    # ========================================================
    # TITLE
    # ========================================================

    report_title = summary.get(
        "title",
        "YouTube AI Video Analysis"
    )

    if not report_title:

        report_title = (
            "YouTube AI Video Analysis"
        )

    story.append(

        Paragraph(
            escape_xml(report_title),
            title_style
        )
    )

    # ========================================================
    # GENERATED DATE
    # ========================================================

    generated_date = datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    story.append(

        Paragraph(

            escape_xml(
                f"Generated: {generated_date}"
            ),

            small_style
        )
    )

    story.append(
        Spacer(1, 15)
    )

    # ========================================================
    # VIDEO
    # ========================================================

    story.append(

        Paragraph(
            "Video",
            heading_style
        )
    )

    if youtube_url:

        story.append(

            Paragraph(

                escape_xml(youtube_url),

                small_style
            )
        )

    else:

        story.append(

            Paragraph(
                "YouTube URL not available.",
                small_style
            )
        )

    story.append(
        Spacer(1, 10)
    )

    # ========================================================
    # EXECUTIVE SUMMARY
    # ========================================================

    story.append(

        Paragraph(
            "Executive Summary",
            heading_style
        )
    )

    executive_summary = summary.get(
        "executive_summary",
        ""
    )

    if not executive_summary:

        executive_summary = (
            "No executive summary was generated."
        )

    story.append(

        Paragraph(

            escape_xml(
                executive_summary
            ),

            body_style
        )
    )

    # ========================================================
    # KEY TAKEAWAYS
    # ========================================================

    story.append(

        Paragraph(
            "Key Takeaways",
            heading_style
        )
    )

    key_takeaways = summary.get(
        "key_takeaways",
        []
    )

    key_takeaways = normalize_list(
        key_takeaways
    )

    if key_takeaways:

        for index, item in enumerate(
            key_takeaways,
            start=1
        ):

            if isinstance(item, dict):

                item_text = (
                    item.get(
                        "point",
                        item.get(
                            "text",
                            item.get(
                                "takeaway",
                                ""
                            )
                        )
                    )
                )

            else:

                item_text = item

            story.append(

                Paragraph(

                    f"{index}. "
                    f"{escape_xml(item_text)}",

                    body_style
                )
            )

    else:

        story.append(

            Paragraph(

                "No key takeaways generated.",

                body_style
            )
        )

    # ========================================================
    # IMPORTANT CONCEPTS
    # ========================================================

    story.append(

        Paragraph(
            "Important Concepts",
            heading_style
        )
    )

    concepts = summary.get(
        "important_concepts",
        []
    )

    concepts = normalize_list(
        concepts
    )

    if concepts:

        for index, concept in enumerate(
            concepts,
            start=1
        ):

            if isinstance(concept, dict):

                concept_text = (
                    concept.get(
                        "concept",
                        concept.get(
                            "name",
                            concept.get(
                                "text",
                                ""
                            )
                        )
                    )
                )

            else:

                concept_text = concept

            story.append(

                Paragraph(

                    f"{index}. "
                    f"{escape_xml(concept_text)}",

                    body_style
                )
            )

    else:

        story.append(

            Paragraph(

                "No important concepts generated.",

                body_style
            )
        )

    # ========================================================
    # ACTION ITEMS
    # ========================================================

    story.append(

        Paragraph(
            "Action Items",
            heading_style
        )
    )

    if action_items:

        data = [

            [
                Paragraph(
                    "No.",
                    table_header_style
                ),

                Paragraph(
                    "Action",
                    table_header_style
                ),

                Paragraph(
                    "Priority",
                    table_header_style
                ),

                Paragraph(
                    "Details / Reason",
                    table_header_style
                ),
            ]
        ]

        for index, item in enumerate(
            action_items,
            start=1
        ):

            if isinstance(item, dict):

                action = item.get(
                    "action",
                    ""
                )

                priority = item.get(
                    "priority",
                    ""
                )

                reason = item.get(
                    "reason",
                    item.get(
                        "details",
                        ""
                    )
                )

            else:

                action = str(item)

                priority = ""

                reason = ""

            data.append(

                [

                    Paragraph(
                        escape_xml(index),
                        small_style
                    ),

                    Paragraph(
                        escape_xml(action),
                        small_style
                    ),

                    Paragraph(
                        escape_xml(priority),
                        small_style
                    ),

                    Paragraph(
                        escape_xml(reason),
                        small_style
                    ),
                ]
            )

        # ====================================================
        # ACTION TABLE
        # ====================================================

        action_table = Table(

            data,

            colWidths=[
                35,
                180,
                65,
                180,
            ],

            repeatRows=1,

            hAlign="LEFT",
        )

        action_table.setStyle(

            TableStyle(
                [

                    # ------------------------------------------------
                    # Header
                    # ------------------------------------------------

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.black,
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    # ------------------------------------------------
                    # Grid
                    # ------------------------------------------------

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),

                    # ------------------------------------------------
                    # Alignment
                    # ------------------------------------------------

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),

                    (
                        "ALIGN",
                        (0, 1),
                        (0, -1),
                        "CENTER",
                    ),

                    (
                        "ALIGN",
                        (2, 1),
                        (2, -1),
                        "CENTER",
                    ),

                    # ------------------------------------------------
                    # Padding
                    # ------------------------------------------------

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(
            KeepTogether(
                action_table
            )
        )

    else:

        story.append(

            Paragraph(

                "No action items generated.",

                body_style
            )
        )

    # ========================================================
    # CONCLUSION
    # ========================================================

    story.append(

        Paragraph(
            "Conclusion",
            heading_style
        )
    )

    conclusion = summary.get(
        "conclusion",
        ""
    )

    if not conclusion:

        conclusion = (
            "No conclusion was generated."
        )

    story.append(

        Paragraph(

            escape_xml(conclusion),

            body_style
        )
    )

    # ========================================================
    # EVALUATION
    # ========================================================

    story.append(

        Paragraph(
            "Evaluation",
            heading_style
        )
    )

    quality_score = evaluation.get(
        "quality_score",
        "N/A"
    )

    summary_score = evaluation.get(
        "summary_score",
        "N/A"
    )

    action_score = evaluation.get(
        "action_items_score",
        "N/A"
    )

    feedback = evaluation.get(
        "feedback",
        ""
    )

    # --------------------------------------------------------
    # Clean scores
    # --------------------------------------------------------

    def format_score(score):

        if score is None:
            return "N/A"

        if score == "":
            return "N/A"

        return str(score)

    quality_score = format_score(
        quality_score
    )

    summary_score = format_score(
        summary_score
    )

    action_score = format_score(
        action_score
    )

    evaluation_data = [

        [
            Paragraph(
                "Metric",
                table_header_style
            ),

            Paragraph(
                "Score",
                table_header_style
            ),
        ],

        [
            Paragraph(
                "Overall Quality",
                small_style
            ),

            Paragraph(
                f"{escape_xml(quality_score)}/10",
                small_style
            ),
        ],

        [
            Paragraph(
                "Summary",
                small_style
            ),

            Paragraph(
                f"{escape_xml(summary_score)}/10",
                small_style
            ),
        ],

        [
            Paragraph(
                "Action Items",
                small_style
            ),

            Paragraph(
                f"{escape_xml(action_score)}/10",
                small_style
            ),
        ],
    ]

    evaluation_table = Table(

        evaluation_data,

        colWidths=[
            250,
            120
        ],

        hAlign="LEFT",
    )

    evaluation_table.setStyle(

        TableStyle(
            [

                # ------------------------------------------------
                # Header
                # ------------------------------------------------

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey,
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),

                # ------------------------------------------------
                # Grid
                # ------------------------------------------------

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),

                # ------------------------------------------------
                # Score alignment
                # ------------------------------------------------

                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "CENTER",
                ),

                # ------------------------------------------------
                # Vertical alignment
                # ------------------------------------------------

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                # ------------------------------------------------
                # Padding
                # ------------------------------------------------

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    story.append(
        evaluation_table
    )

    story.append(
        Spacer(1, 10)
    )

    # ========================================================
    # EVALUATOR FEEDBACK
    # ========================================================

    if feedback:

        feedback_text = (
            "<b>Evaluator Feedback:</b> "
            f"{escape_xml(feedback)}"
        )

    else:

        feedback_text = (
            "<b>Evaluator Feedback:</b> "
            "No evaluator feedback was generated."
        )

    story.append(

        Paragraph(

            feedback_text,

            body_style
        )
    )

    # ========================================================
    # FOOTER
    # ========================================================

    story.append(
        Spacer(1, 20)
    )

    story.append(

        Paragraph(

            "Generated by YouTube AI Video Analyzer",

            small_style
        )
    )

    # ========================================================
    # BUILD PDF
    # ========================================================

    try:

        document.build(
            story
        )

    except Exception as e:

        print(
            f"[PDF] PDF build failed: {e}"
        )

        raise

    # ========================================================
    # VALIDATE PDF
    # ========================================================

    if not pdf_path.exists():

        raise RuntimeError(
            "PDF generation completed but "
            "file was not created."
        )

    pdf_size = pdf_path.stat().st_size

    if pdf_size <= 0:

        raise RuntimeError(
            "Generated PDF is empty."
        )

    # ========================================================
    # LOG SUCCESS
    # ========================================================

    print()
    print(
        "=========================================================="
    )

    print(
        "[PDF] PDF generated successfully"
    )

    print(
        f"[PDF] File: {pdf_path}"
    )

    print(
        f"[PDF] Size: {pdf_size} bytes"
    )

    print(
        "=========================================================="
    )

    # ========================================================
    # RETURN
    # ========================================================

    return str(
        pdf_path.resolve()
    )