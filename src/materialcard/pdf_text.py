"""PDF text extraction utilities."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from .exceptions import NonTextPdfError


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF file."""

    reader = PdfReader(str(path))
    pages_text: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages_text.append(page_text)
    return "\n".join(pages_text)


def ensure_text_pdf(text: str, *, min_chars: int = 200) -> str:
    """Ensure the PDF contains sufficient text for parsing."""

    normalized = text.strip()
    if len(normalized) < min_chars:
        raise NonTextPdfError(
            f"PDF text too short: {len(normalized)} chars (min {min_chars})."
        )
    return normalized
