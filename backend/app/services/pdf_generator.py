# ============================================================
# PDF GENERATOR
# ============================================================

from pathlib import Path
from datetime import datetime
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """
    Convert Unicode text into PDF-safe ASCII text.

    This prevents black square boxes caused by unsupported
    Unicode characters in ReportLab fonts.
    """

    if value is None:
        return ""

    # --------------------------------------------------------
    # Convert everything to string
    # --------------------------------------------------------

    text = str(value)

    # --------------------------------------------------------
    # Unicode normalization
    # --------------------------------------------------------

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    # --------------------------------------------------------
    # Replace problematic Unicode characters
    # --------------------------------------------------------

    replacements = {

        # Hyphens / dashes
        "\u2010": "-",   # hyphen
        "\u2011": "-",   # non-breaking hyphen
        "\u2012": "-",   # figure dash
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2015": "-",   # horizontal bar
        "\u2212": "-",   # minus sign

        # Bullets
        "\u2022": "-",
        "\u2023": "-",
        "\u25CF": "-",
        "\u25AA": "-",
        "\u25AB": "-",

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

        # Zero width characters
        "\u200B": "",
        "\u200C": "",
        "\u200D": "",
        "\u2060": "",
        "\uFEFF": "",

        # Other common symbols
        "\u00AD": "-",    # soft hyphen
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    # --------------------------------------------------------
    # Remove remaining control characters
    # --------------------------------------------------------

    text = "".join(
        ch
        for ch in text
        if ch in "\n\r\t"
        or ord(ch) >= 32
    )

    # --------------------------------------------------------
    # Convert remaining non-ASCII characters
    #
    # Example:
    # café -> cafe
    # naïve -> naive
    # --------------------------------------------------------

    text = (
        unicodedata
        .normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    # --------------------------------------------------------
    # Clean excessive whitespace
    # --------------------------------------------------------

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
# HTML / REPORTLAB ESCAPING
# ============================================================

def escape_xml(text):
    """
    Escape characters that have special meaning in ReportLab
    Paragraph XML.
    """

    text = clean_text(text)

    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return text


# ============================================================
# PARAGRAPH HELPER
# ============================================================

def make_paragraph(
    text,
    style
):
    """
    Always clean text before sending it to ReportLab.
    """

    return Paragraph(
        escape_xml(text),
        style
    )


# ============================================================
# STYLES
# ============================================================

styles = getSampleStyleSheet()


TITLE_STYLE = ParagraphStyle(
    "CustomTitle",

    parent=styles["Title"],

    fontName="Helvetica-Bold",

    fontSize=20,

    leading=24,

    alignment=TA_CENTER,

    spaceAfter=10,

    textColor=colors.HexColor(
        "#1F5FE8"
    ),
)


SUBTITLE_STYLE = ParagraphStyle(
    "Subtitle",

    parent=styles["Normal"],

    fontName="Helvetica",

    fontSize=9,

    leading=12,

    alignment=TA_CENTER,

    spaceAfter=15,
)


HEADING_STYLE = ParagraphStyle(
    "Heading",

    parent=styles["Heading2"],

    fontName="Helvetica-Bold",

    fontSize=14,

    leading=18,

    spaceBefore=8,

    spaceAfter=8,

    textColor=colors.HexColor(
        "#2463EB"
    ),
)


BODY_STYLE = ParagraphStyle(
    "Body",

    parent=styles["BodyText"],

    fontName="Helvetica",

    fontSize=10,

    leading=14,

    spaceAfter=6,
)


BULLET_STYLE = ParagraphStyle(
    "Bullet",

    parent=BODY_STYLE,

    leftIndent=12,

    firstLineIndent=-8,

    spaceAfter=5,
)


SMALL_STYLE = ParagraphStyle(
    "Small",

    parent=styles["Normal"],

    fontName="Helvetica",

    fontSize=8,

    leading=10,
)


# ============================================================
# PAGE NUMBER
# ============================================================

def add_page_number(
    canvas,
    doc
):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.setFillColor(
        colors.grey
    )

    canvas.drawCentredString(
        A4[0] / 2,
        12 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# NORMALIZE LIST
# ============================================================

def normalize_list(value):

    if value is None:
        return []

    if isinstance(value, list):

        return value

    return [value]


# ============================================================
# GET VALUE
# ============================================================

def get_value(
    data,
    key,
    default=""
):

    if not isinstance(data, dict):

        return default

    value = data.get(
        key,
        default
    )

    if value is None:

        return default

    return value


# ============================================================
# GENERATE PDF
# ============================================================

def generate_pdf(
    youtube_url,
    summary=None,
    action_items=None,
    evaluation=None,
    quality_score=0,
    output_filename=None
):

    # --------------------------------------------------------
    # Normalize input
    # --------------------------------------------------------

    summary = summary or {}

    action_items = (
        action_items
        or []
    )

    evaluation = (
        evaluation
        or {}
    )

    # --------------------------------------------------------
    # Filename
    # --------------------------------------------------------

    if not output_filename:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_filename = (
            f"youtube_analysis_{timestamp}.pdf"
        )

    output_path = (
        OUTPUT_DIR /
        output_filename
    )

    # --------------------------------------------------------
    # Document
    # --------------------------------------------------------

    document = SimpleDocTemplate(

        str(output_path),

        pagesize=A4,

        rightMargin=18 * mm,

        leftMargin=18 * mm,

        topMargin=18 * mm,

        bottomMargin=20 * mm,

        title="YouTube Video Analysis",

        author="YouTube AI Analyzer"
    )

    story = []

    # ========================================================
    # TITLE
    # ========================================================

    story.append(
        make_paragraph(
            "YouTube AI Video Analysis",
            TITLE_STYLE
        )
    )

    story.append(
        make_paragraph(
            f"Video: {youtube_url}",
            SUBTITLE_STYLE
        )
    )

    story.append(
        Spacer(
            1,
            5
        )
    )

    # ========================================================
    # EXECUTIVE SUMMARY
    # ========================================================

    story.append(
        make_paragraph(
            "EXECUTIVE SUMMARY",
            HEADING_STYLE
        )
    )

    executive_summary = get_value(
        summary,
        "executive_summary",
        ""
    )

    if not executive_summary:

        executive_summary = get_value(
            summary,
            "summary",
            ""
        )

    if not executive_summary:

        executive_summary = (
            "No executive summary was generated."
        )

    story.append(
        make_paragraph(
            executive_summary,
            BODY_STYLE
        )
    )

    # ========================================================
    # KEY POINTS
    # ========================================================

    story.append(
        make_paragraph(
            "KEY POINTS",
            HEADING_STYLE
        )
    )

    key_points = get_value(
        summary,
        "key_points",
        []
    )

    key_points = normalize_list(
        key_points
    )

    if not key_points:

        key_points = [
            "No key points were generated."
        ]

    for point in key_points:

        clean_point = clean_text(
            point
        )

        # Always use ASCII hyphen
        # instead of Unicode bullet

        bullet_text = (
            "- "
            + clean_point
        )

        story.append(
            make_paragraph(
                bullet_text,
                BULLET_STYLE
            )
        )

    # ========================================================
    # ACTION ITEMS
    # ========================================================

    story.append(
        make_paragraph(
            "ACTION ITEMS",
            HEADING_STYLE
        )
    )

    action_items = normalize_list(
        action_items
    )

    table_data = [

        [
            make_paragraph(
                "Priority",
                SMALL_STYLE
            ),

            make_paragraph(
                "Action",
                SMALL_STYLE
            )
        ]
    ]

    if action_items:

        for item in action_items:

            if isinstance(
                item,
                dict
            ):

                priority = get_value(
                    item,
                    "priority",
                    "MEDIUM"
                )

                action = get_value(
                    item,
                    "action",
                    ""
                )

                reason = get_value(
                    item,
                    "reason",
                    ""
                )

                action_text = (
                    clean_text(action)
                )

                if reason:

                    action_text += (
                        "<br/><font size='8'>"
                        "Reason: "
                        + escape_xml(reason)
                        + "</font>"
                    )

                table_data.append(

                    [

                        make_paragraph(
                            priority,
                            SMALL_STYLE
                        ),

                        Paragraph(
                            action_text,
                            SMALL_STYLE
                        )

                    ]
                )

            else:

                table_data.append(

                    [

                        make_paragraph(
                            "MEDIUM",
                            SMALL_STYLE
                        ),

                        make_paragraph(
                            item,
                            SMALL_STYLE
                        )

                    ]
                )

    else:

        table_data.append(

            [

                make_paragraph(
                    "INFO",
                    SMALL_STYLE
                ),

                make_paragraph(
                    "No action items were identified.",
                    SMALL_STYLE
                )

            ]
        )

    action_table = Table(

        table_data,

        colWidths=[
            35 * mm,
            125 * mm
        ],

        repeatRows=1
    )

    action_table.setStyle(

        TableStyle(

            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E5E7EB")
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#D1D5DB")
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),

            ]

        )
    )

    story.append(
        action_table
    )

    # ========================================================
    # EVALUATION
    # ========================================================

    story.append(
        make_paragraph(
            "QUALITY EVALUATION",
            HEADING_STYLE
        )
    )

    score_text = (
        f"Overall Quality Score: "
        f"{clean_text(quality_score)}/100"
    )

    story.append(
        make_paragraph(
            score_text,
            BODY_STYLE
        )
    )

    if evaluation:

        evaluation_text = get_value(
            evaluation,
            "feedback",
            ""
        )

        if evaluation_text:

            story.append(
                make_paragraph(
                    evaluation_text,
                    BODY_STYLE
                )
            )

    # ========================================================
    # BUILD PDF
    # ========================================================

    document.build(

        story,

        onFirstPage=add_page_number,

        onLaterPages=add_page_number
    )

    # ========================================================
    # VERIFY
    # ========================================================

    if not output_path.exists():

        raise RuntimeError(
            "PDF generation failed."
        )

    if output_path.stat().st_size == 0:

        raise RuntimeError(
            "Generated PDF is empty."
        )

    print(
        f"PDF generated successfully: "
        f"{output_path}"
    )

    return str(output_path)