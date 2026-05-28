import re
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer


def render_pdf(
    report_markdown: str,
    customer_name: str,
    report_type: str,
    chart_paths: Optional[List[Path]] = None,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=48,
        leftMargin=48,
        topMargin=48,
        bottomMargin=48,
        title=f"{report_type} - {customer_name}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph(_escape(f"{report_type} — {customer_name}"), title_style))
    story.append(Spacer(1, 0.15 * inch))

    for block in _markdown_blocks(report_markdown):
        if block["type"] == "heading":
            story.append(Paragraph(_escape(block["text"]), heading_style))
        elif block["type"] == "bullet":
            story.append(Paragraph(_escape(f"• {block['text']}"), body_style))
        else:
            story.append(Paragraph(_escape(block["text"]), body_style))

    if chart_paths:
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(_escape("Performance Charts"), heading_style))
        for chart_path in chart_paths:
            if not chart_path.exists():
                continue
            img = Image(str(chart_path))
            img.drawWidth = 6.5 * inch
            img.drawHeight = 3.6 * inch
            story.append(Spacer(1, 0.1 * inch))
            story.append(img)

    doc.build(story)
    return buffer.getvalue()


def _markdown_blocks(markdown: str) -> List[dict]:
    blocks: List[dict] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append({"type": "heading", "text": line[4:].strip()})
        elif line.startswith("## "):
            blocks.append({"type": "heading", "text": line[3:].strip()})
        elif line.startswith("# "):
            blocks.append({"type": "heading", "text": line[2:].strip()})
        elif line.startswith("- "):
            blocks.append({"type": "bullet", "text": line[2:].strip()})
        else:
            blocks.append({"type": "paragraph", "text": line})
    return blocks


def _escape(text: str) -> str:
    return re.sub(r"[`_*]", "", text)
