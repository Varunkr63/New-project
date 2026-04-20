from __future__ import annotations

from io import BytesIO


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
