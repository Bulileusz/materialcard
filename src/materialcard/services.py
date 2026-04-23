"""Application-level workflows for materialcard."""

from __future__ import annotations

from pathlib import Path

from .builder import build_approval_request
from .context_io import load_context
from .models import ApprovalContext, ApprovalRequestData, MaterialData
from .parse_regex import parse_material_from_text
from .pdf_text import ensure_text_pdf, extract_text_from_pdf
from .renderer_docx import render_docx


def _parse_material_from_pdf(pdf_path: Path, min_chars: int) -> MaterialData:
    text = extract_text_from_pdf(pdf_path)
    text = ensure_text_pdf(text, min_chars=min_chars)
    return parse_material_from_text(text, source_path=str(pdf_path))


def generate_docx_from_pdf(
    pdf_path: Path,
    context_path: Path,
    template_path: Path,
    output_path: Path,
    *,
    min_chars: int = 200,
    context_data: ApprovalContext | None = None,
) -> ApprovalRequestData:
    """Generate a DOCX approval request from a PDF and project context."""

    material = _parse_material_from_pdf(pdf_path, min_chars)
    ctx = context_data if context_data is not None else load_context(context_path)
    data = build_approval_request(material, ctx)
    render_docx(data, template_path, output_path)
    return data
