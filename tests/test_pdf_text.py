"""Tests for pdf_text utilities."""

import pytest

from materialcard.exceptions import NonTextPdfError
from materialcard.pdf_text import ensure_text_pdf


def test_ensure_text_pdf_raises_on_short_text() -> None:
    with pytest.raises(NonTextPdfError):
        ensure_text_pdf("short", min_chars=10)


def test_ensure_text_pdf_returns_text() -> None:
    text = "x" * 250
    assert ensure_text_pdf(text, min_chars=200) == text
