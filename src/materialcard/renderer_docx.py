"""DOCX rendering (placeholder)."""

from __future__ import annotations

from pathlib import Path

from .exceptions import RenderError
from .models import ApprovalRequestData


def render_docx(
    data: ApprovalRequestData,
    template_path: Path,
    output_path: Path,
) -> None:
    """Render an approval request to DOCX."""

    if not template_path.exists():
        raise RenderError(f"Template not found: {template_path}")

    try:
        from docxtpl import DocxTemplate
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RenderError("docxtpl is not installed.") from exc

    DocxTemplate
    raise NotImplementedError("DOCX rendering not implemented yet.")
