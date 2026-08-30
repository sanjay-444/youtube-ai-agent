from pathlib import Path
from datetime import datetime
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = BASE_DIR / "fonts"


# ============================================================
# FONTS
# ============================================================

REGULAR_FONT = FONT_DIR / "DejaVuSans.ttf"
BOLD_FONT = FONT_DIR / "DejaVuSans-Bold.ttf"


if not REGULAR_FONT.exists():
    raise RuntimeError(
        f"Font not found:\n{REGULAR_FONT}\n\n"
        "Please download DejaVuSans.ttf and place it in the fonts folder."
    )


if not BOLD_FONT.exists():
    raise RuntimeError(
        f"Font not found:\n{BOLD_FONT}\n\n"
        "Please download DejaVuSans-Bold.ttf and place it in the fonts folder."
    )


pdfmetrics.registerFont(
    TTFont(
        "DejaVuSans",
        str(REGULAR_FONT)
    )
)

pdfmetrics.registerFont(
    TTFont(
        "DejaVuSans-Bold",
        str(BOLD_FONT)
    )
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """
    Clean AI generated text before putting it into the PDF.

    This prevents unsupported Unicode characters from becoming
    black square/block characters.
    """

    if value is None:
        return ""

    value = str(value)

    # --------------------------------------------------------
    # Unicode normalization
    # --------------------------------------------------------

    value = unicodedata.normalize(
        "NFKC",
        value
    )

    # --------------------------------------------------------
    # Replace different dash characters
    # --------------------------------------------------------

    dash_replacements = {

        "\u2010": "-",   # Hyphen

        "\u2011": "-",   # Non-breaking hyphen

        "\u2012": "-",   # Figure dash

        "\u2013": "-",   # En dash

        "\u2014": "-",   # Em dash

        "\u2015": "-",   # Horizontal bar

        "\u2212": "-",   # Minus sign

        "\ufe58": "-",   # Small em dash

        "\ufe63": "-",   # Small hyphen-minus

        "\uff0d": "-",   # Full-width hyphen
    }

    for old, new in dash_replacements.items():
        value = value.replace(old, new)


    # --------------------------------------------------------
    # Replace smart quotes
    # --------------------------------------------------------

    quote_replacements = {

        "\u2018": "'",

        "\u2019": "'",

        "\u201a": "'",

        "\u201b": "'",

        "\u201c": '"',

        "\u201d": '"',

        "\u201e": '"',

        "\u201f": '"',
    }

    for old, new in quote_replacements.items():
        value = value.replace(old, new)


    # --------------------------------------------------------
    # Other common Unicode characters
    # --------------------------------------------------------

    other_replacements = {

        "\u00a0": " ",      # Non-breaking space

        "\u2026": "...",    # Ellipsis

        "\u2022": "-",      # Bullet

        "\u25cf": "-",      # Black circle

        "\u25aa": "-",      # Small square

        "\u00b7": "-",      # Middle dot

        "\u00d7": "x",      # Multiplication sign

        "\u00f7": "/",      # Division sign

        "\u2192": "->",     # Right arrow

        "\u2190": "<-",     # Left arrow

        "\u21d2": "=>",     # Double right arrow

        "\u2713": "[OK]",   # Check mark

        "\u2714": "[OK]",   # Heavy check mark

        "\u2717": "[X]",    # Cross

        "\u2718": "[X]",    # Heavy cross

    }

    for old, new in other_replacements.items():
        value = value.replace(old, new)


    # --------------------------------------------------------
    # Remove zero-width characters
    # --------------------------------------------------------

    zero_width_chars = [

        "\u200b",

        "\u200c",

        "\u200d",

        "\u2060",

        "\ufeff",
    ]

    for char in zero_width_chars:
        value = value.replace(char, "")


    # --------------------------------------------------------
    # Remove control characters except newline/tab
    # --------------------------------------------------------

    cleaned = []

    for char in value:

        category = unicodedata.category(char)

        if category.startswith("C"):

            if char in ("\n", "\t", "\r"):
                cleaned.append(char)

            continue

        cleaned.append(char)

    value = "".join(cleaned)


    # --------------------------------------------------------
    # Clean excessive spaces
    # --------------------------------------------------------

    value = re.sub(
        r"[ \t]+",
        " ",
        value
    )

    value = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        value
    )

    return value.strip()


# ============================================================
# ESCAPE TEXT FOR REPORTLAB
# ============================================================

def paragraph_text(value):

    value = clean_text(value)

    # ReportLab Paragraph treats these as HTML/XML.
    value = (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    value = value.replace(
        "\n",
        "<br/>"
    )

    return value


# ============================================================
# PAGE HEADER / FOOTER
# ============================================================

def draw_page(canvas, doc):

    canvas.saveState()

    width, height = A4

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    canvas.setFont(
        "DejaVuSans",
        8
    )

    canvas.setFillColor(
        colors.grey
    )

    canvas.drawCentredString(
        width / 2,
        12 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# CREATE PDF
# ============================================================

def generate_pdf(
    analysis,
    youtube_url=""
):

    # --------------------------------------------------------
    # File name
    # --------------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    pdf_path = (
        OUTPUT_DIR /
        f"youtube_analysis_{timestamp}.pdf"
    )


    # --------------------------------------------------------
    # Document
    # --------------------------------------------------------

    doc = SimpleDocTemplate(

        str(pdf_path),

        pagesize=A4,

        rightMargin=18 * mm,

        leftMargin=18 * mm,

        topMargin=18 * mm,

        bottomMargin=20 * mm,

        title="YouTube AI Video Analysis",

        author="YouTube AI Video Analyzer",
    )


    # --------------------------------------------------------
    # Styles
    # --------------------------------------------------------

    styles = getSampleStyleSheet()


    title_style = ParagraphStyle(

        "CustomTitle",

        parent=styles["Title"],

        fontName="DejaVuSans-Bold",

        fontSize=22,

        leading=27,

        alignment=TA_CENTER,

        spaceAfter=12,

        textColor=colors.HexColor(
            "#2563EB"
        ),
    )


    subtitle_style = ParagraphStyle(

        "Subtitle",

        parent=styles["Normal"],

        fontName="DejaVuSans",

        fontSize=9,

        leading=13,

        alignment=TA_CENTER,

        spaceAfter=16,

        textColor=colors.grey,
    )


    heading_style = ParagraphStyle(

        "Heading",

        parent=styles["Heading2"],

        fontName="DejaVuSans-Bold",

        fontSize=14,

        leading=18,

        spaceBefore=12,

        spaceAfter=8,

        textColor=colors.HexColor(
            "#2563EB"
        ),
    )


    body_style = ParagraphStyle(

        "Body",

        parent=styles["BodyText"],

        fontName="DejaVuSans",

        fontSize=9.5,

        leading=14,

        spaceAfter=6,

        textColor=colors.HexColor(
            "#222222"
        ),
    )


    bullet_style = ParagraphStyle(

        "Bullet",

        parent=body_style,

        leftIndent=12,

        firstLineIndent=-8,

        spaceAfter=5,
    )


    table_style = ParagraphStyle(

        "Table",

        parent=body_style,

        fontSize=8.5,

        leading=12,
    )


    # --------------------------------------------------------
    # Story
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if youtube_url:

        story.append(
            Paragraph(
                paragraph_text(youtube_url),
                subtitle_style
            )
        )


    story.append(
        Spacer(
            1,
            5 * mm
        )
    )


    # ========================================================
    # EXECUTIVE SUMMARY
    # ========================================================

    story.append(
        Paragraph(
            "EXECUTIVE SUMMARY",
            heading_style
        )
    )


    summary = analysis.get(
        "executive_summary",
        analysis.get(
            "summary",
            ""
        )
    )


    if isinstance(summary, dict):

        summary = (
            summary.get(
                "executive_summary",
                ""
            )
        )


    summary = clean_text(summary)


    if summary:

        story.append(
            Paragraph(
                paragraph_text(summary),
                body_style
            )
        )

    else:

        story.append(
            Paragraph(
                "No executive summary was generated.",
                body_style
            )
        )


    # ========================================================
    # KEY POINTS
    # ========================================================

    story.append(
        Paragraph(
            "KEY POINTS",
            heading_style
        )
    )


    key_points = analysis.get(
        "key_points",
        []
    )


    if isinstance(
        key_points,
        str
    ):

        key_points = [
            key_points
        ]


    if not key_points:

        story.append(
            Paragraph(
                "No key points were generated.",
                body_style
            )
        )

    else:

        for point in key_points:

            point = clean_text(point)

            if not point:
                continue

            story.append(
                Paragraph(
                    "- " +
                    paragraph_text(point),
                    bullet_style
                )
            )


    # ========================================================
    # ACTION ITEMS
    # ========================================================

    story.append(
        Paragraph(
            "ACTION ITEMS",
            heading_style
        )
    )


    action_items = analysis.get(
        "action_items",
        []
    )


    if not action_items:

        story.append(
            Paragraph(
                "No action items were generated.",
                body_style
            )
        )

    else:

        table_data = [

            [
                Paragraph(
                    "<b>Priority</b>",
                    table_style
                ),

                Paragraph(
                    "<b>Action</b>",
                    table_style
                )
            ]
        ]


        for item in action_items:

            # ------------------------------------------------
            # Dictionary format
            # ------------------------------------------------

            if isinstance(
                item,
                dict
            ):

                priority = clean_text(
                    item.get(
                        "priority",
                        "MEDIUM"
                    )
                )

                action = clean_text(
                    item.get(
                        "action",
                        ""
                    )
                )

                reason = clean_text(
                    item.get(
                        "reason",
                        ""
                    )
                )

                if reason:

                    action = (
                        action +
                        "<br/><font size='7'>"
                        "Reason: " +
                        paragraph_text(reason) +
                        "</font>"
                    )

                else:

                    action = paragraph_text(
                        action
                    )


            # ------------------------------------------------
            # String format
            # ------------------------------------------------

            else:

                priority = "MEDIUM"

                action = paragraph_text(
                    clean_text(item)
                )


            table_data.append(

                [

                    Paragraph(
                        paragraph_text(
                            priority
                        ),
                        table_style
                    ),

                    Paragraph(
                        action,
                        table_style
                    )
                ]
            )


        action_table = Table(

            table_data,

            colWidths=[
                32 * mm,
                130 * mm
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
                        colors.HexColor(
                            "#E5E7EB"
                        )
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#111827"
                        )
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor(
                            "#D1D5DB"
                        )
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
                        6
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),
                ]
            )
        )


        story.append(
            action_table
        )


    # ========================================================
    # CONCLUSION
    # ========================================================

    conclusion = analysis.get(
        "conclusion",
        ""
    )


    if conclusion:

        story.append(
            Paragraph(
                "CONCLUSION",
                heading_style
            )
        )

        story.append(
            Paragraph(
                paragraph_text(
                    conclusion
                ),
                body_style
            )
        )


    # ========================================================
    # BUILD
    # ========================================================

    doc.build(

        story,

        onFirstPage=draw_page,

        onLaterPages=draw_page
    )


    # ========================================================
    # VALIDATE
    # ========================================================

    if not pdf_path.exists():

        raise RuntimeError(
            "PDF was not generated."
        )


    if pdf_path.stat().st_size == 0:

        raise RuntimeError(
            "Generated PDF is empty."
        )


    print(
        f"PDF generated successfully: {pdf_path}"
    )


    return str(pdf_path)