"""Renderer tests (placeholder)."""

from materialcard.exceptions import RenderError
from materialcard.models import ApprovalRequestData, MaterialData
from materialcard.renderer_docx import render_docx


def test_render_docx_invalid_template(tmp_path) -> None:
    template = tmp_path / "template.docx"
    template.write_text("placeholder", encoding="utf-8")
    material = MaterialData(
        material_type="Material",
        description="Desc",
    )
    data = ApprovalRequestData(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        material_type=material.material_type,
        manufacturer="Manufacturer",
        estimated_quantity="10",
        description=material.description,
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        attachments=[],
        attachments_text="—",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
    )
    output = tmp_path / "out.docx"

    try:
        render_docx(data, template, output)
    except RenderError:
        return
    raise AssertionError("Expected RenderError for invalid DOCX template.")
