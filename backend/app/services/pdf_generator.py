import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# VERCEL-SAFE OUTPUT DIRECTORY
# ============================================================
#
# Vercel's deployed filesystem is read-only.
#
# DO NOT use:
#
#     Path("output")
#
#     /var/task/output
#
# Instead, use the temporary writable directory.
#
# Files stored here are temporary and should be returned
# immediately to the client.
#
# ============================================================

OUTPUT_DIR = Path(tempfile.gettempdir()) / "youtube_ai_agent"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """
    Convert any value into clean text suitable for a PDF.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value)


# ============================================================
# HTML / REPORTLAB SAFE TEXT
# ============================================================

def pdf_safe(value):
    """
    Convert text into a format that ReportLab can safely render.

    This protects the PDF generator from common special
    characters and accidental HTML characters.
    """

    text = clean_text(value)

    if not text:
        return ""

    # Remove null characters
    text = text.replace("\x00", "")

    # Common Unicode replacements
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2026": "...",
        "\u00a0": " ",
        "\u2022": "-",
        "\u2192": "->",
        "\u00b7": "-",
        "\u2713": "OK",
        "\u2714": "OK",
        "\u2717": "X",
        "\u2718": "X",
        "\u26a0": "Warning",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


# ============================================================
# ESCAPE REPORTLAB XML
# ============================================================

def escape_xml(value):
    """
    Escape characters that ReportLab Paragraph interprets
    as XML/HTML.

    This prevents errors when AI-generated text contains:
        <
        >
        &
    """

    text = pdf_safe(value)

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
    Generate a PDF report from the AI analysis.

    Vercel-safe implementation.

    Parameters
    ----------
    summary:
        Dictionary containing:
            executive_summary
            key_takeaways
            important_concepts
            conclusion

    action_items:
        List of dictionaries containing:
            action
            priority
            reason/details

    evaluation:
        Dictionary containing:
            quality_score
            summary_score
            action_items_score
            feedback

    youtube_url:
        Original YouTube video URL.

    output_dir:
        Optional custom output directory.

        If not supplied, the Vercel-safe temporary directory
        is used.

    Returns
    -------
    str
        Absolute path to generated PDF.
    """

    # ========================================================
    # OUTPUT DIRECTORY
    # ========================================================

    if output_dir is None:
        output_path = OUTPUT_DIR
    else:
        output_path = Path(output_dir)

    # Make sure directory exists
    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # FILE NAME
    # ========================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    filename = (
        f"youtube_analysis_{timestamp}.pdf"
    )

    pdf_path = output_path / filename

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
    )

    # ========================================================
    # STYLES
    # ========================================================

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        leading=28,
        spaceAfter=15,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=15,
        leading=19,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=16,
        spaceAfter=8,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=12,
    )

    # ========================================================
    # STORY
    # ========================================================

    story = []

    # ========================================================
    # TITLE
    # ========================================================

    story.append(
        Paragraph(
            "YouTube AI Video Analysis",
            title_style
        )
    )

    story.append(
        Paragraph(
            escape_xml(
                f"Generated: "
                f"{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            ),
            small_style
        )
    )

    story.append(
        Spacer(1, 15)
    )

    # ========================================================
    # VIDEO URL
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
            escape_xml(executive_summary),
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

    if not isinstance(key_takeaways, list):
        key_takeaways = []

    if key_takeaways:

        for index, item in enumerate(
            key_takeaways,
            start=1
        ):

            story.append(
                Paragraph(
                    f"{index}. "
                    f"{escape_xml(item)}",
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

    if not isinstance(concepts, list):
        concepts = []

    if concepts:

        for index, concept in enumerate(
            concepts,
            start=1
        ):

            story.append(
                Paragraph(
                    f"{index}. "
                    f"{escape_xml(concept)}",
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
                "No.",
                "Action",
                "Priority",
                "Details / Reason",
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
                    str(index),

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

        table = Table(
            data,
            colWidths=[
                35,
                180,
                65,
                180,
            ],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [

                    # Header background
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),

                    # Header text
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.black,
                    ),

                    # Header font
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    # Grid
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),

                    # Vertical alignment
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),

                    # Padding
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

        story.append(table)

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

    evaluation_data = [
        [
            "Metric",
            "Score"
        ],
        [
            "Overall Quality",
            f"{quality_score}/10",
        ],
        [
            "Summary",
            f"{summary_score}/10",
        ],
        [
            "Action Items",
            f"{action_score}/10",
        ],
    ]

    evaluation_table = Table(
        evaluation_data,
        colWidths=[
            250,
            120
        ],
    )

    evaluation_table.setStyle(
        TableStyle(
            [

                # Header
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

                # Grid
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),

                # Score alignment
                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "CENTER",
                ),

                # Vertical alignment
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                # Padding
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

    story.append(
        Paragraph(
            f"<b>Evaluator Feedback:</b> "
            f"{escape_xml(feedback)}",
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

    document.build(
        story
    )

    # ========================================================
    # VALIDATE FILE
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

    print()
    print(
        "[PDF] PDF generated successfully:"
    )

    print(
        f"[PDF] {pdf_path}"
    )

    print(
        f"[PDF] Size: {pdf_size} bytes"
    )

    # ========================================================
    # RETURN
    # ========================================================

    return str(
        pdf_path.resolve()
    )