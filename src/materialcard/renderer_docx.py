"""DOCX rendering (placeholder)."""

from __future__ import annotations

from pathlib import Path

from .exceptions import RenderError, TemplateNotFoundError
from .models import ApprovalRequestData


def render_docx(
    data: ApprovalRequestData,
    template_path: Path,
    output_path: Path,
) -> None:
    """Render an approval request to DOCX."""

    if not template_path.exists():
        raise TemplateNotFoundError(f"Template not found: {template_path}")

    try:
        from docxtpl import DocxTemplate
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RenderError("docxtpl is not installed.") from exc

    context = {
        "investor_name": data.investor_name,
        "project_title": data.project_title,
        "contractor_name": data.contractor_name,
        "material_type": data.material_type,
        "manufacturer": data.manufacturer,
        "estimated_quantity": data.estimated_quantity,
        "description": data.description,
        "planned_delivery_date": data.planned_delivery_date,
        "planned_installation_date": data.planned_installation_date,
        "attachments_text": data.attachments_text,
        "prepared_by_name": data.prepared_by_name,
        "prepared_by_role": data.prepared_by_role,
    }

    try:
        doc = DocxTemplate(str(template_path))
        doc.render(context)
        doc.save(str(output_path))
    except Exception as exc:  # noqa: BLE001 - domain error wrapping
        raise RenderError("Failed to render DOCX.") from exc
