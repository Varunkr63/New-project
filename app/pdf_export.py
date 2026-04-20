from __future__ import annotations

from io import BytesIO
from textwrap import wrap


def build_entry_pdf(entry: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    sections = [
        ("Voice Journal Entry", None),
        ("Date", entry["entry_date"]),
        ("Title", entry["title"]),
        ("Mood", f'{entry["mood_label"]} ({entry["mood_score"]})'),
        ("Language", f'{entry["language"]} / detected: {entry["detected_language"]}'),
        ("Insight", entry["insight_summary"]),
        ("Transcript", entry["transcript"]),
        ("Notes", entry["user_notes"] or "No additional notes."),
    ]

    for heading, content in sections:
        pdf.setFont("Helvetica-Bold", 16 if content is None else 11)
        pdf.drawString(50, y, heading)
        y -= 24 if content is None else 18
        if content is None:
            continue
        pdf.setFont("Helvetica", 10)
        for line in wrap(str(content), 90):
            pdf.drawString(50, y, line)
            y -= 14
            if y < 60:
                pdf.showPage()
                y = height - 50
        y -= 10

    pdf.save()
    buffer.seek(0)
    return buffer.read()
