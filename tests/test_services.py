"""Tests for application-level workflows."""

from pathlib import Path

from materialcard.models import ApprovalContext, ApprovalRequestData, MaterialData
from materialcard.services import generate_docx_from_pdf


def test_generate_docx_from_pdf_orchestrates_generate_workflow(monkeypatch) -> None:
    pdf_path = Path("input.pdf")
    context_path = Path("context.json")
    template_path = Path("template.docx")
    output_path = Path("output.docx")
    calls: list[tuple[str, object]] = []

    material = MaterialData(
        source_path=str(pdf_path),
        raw_text="normalized",
        material_type="Material",
        description="Desc",
    )
    context = ApprovalContext(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        manufacturer="Manufacturer",
        estimated_quantity="10",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
        attachments=[],
    )
    approval = ApprovalRequestData(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        material_type="Material",
        manufacturer="Manufacturer",
        estimated_quantity="10",
        description="Desc",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        attachments=[],
        prepared_by_name="Prepared",
        prepared_by_role="Role",
    )

    def fake_extract(path: Path) -> str:
        calls.append(("extract_text_from_pdf", path))
        return "raw pdf text"

    def fake_ensure(text: str, *, min_chars: int) -> str:
        calls.append(("ensure_text_pdf", text, min_chars))
        return "normalized"

    def fake_parse(text: str, *, source_path: str | None = None) -> MaterialData:
        calls.append(("parse_material_from_text", text, source_path))
        return material

    def fake_load_context(path: Path) -> ApprovalContext:
        calls.append(("load_context", path))
        return context

    def fake_build_approval_request(
        parsed_material: MaterialData,
        loaded_context: ApprovalContext,
    ) -> ApprovalRequestData:
        calls.append(("build_approval_request", parsed_material, loaded_context))
        return approval

    def fake_render_docx(
        data: ApprovalRequestData,
        template: Path,
        output: Path,
    ) -> None:
        calls.append(("render_docx", data, template, output))

    monkeypatch.setattr("materialcard.services.extract_text_from_pdf", fake_extract)
    monkeypatch.setattr("materialcard.services.ensure_text_pdf", fake_ensure)
    monkeypatch.setattr("materialcard.services.parse_material_from_text", fake_parse)
    monkeypatch.setattr("materialcard.services.load_context", fake_load_context)
    monkeypatch.setattr("materialcard.services.build_approval_request", fake_build_approval_request)
    monkeypatch.setattr("materialcard.services.render_docx", fake_render_docx)

    result = generate_docx_from_pdf(
        pdf_path,
        context_path,
        template_path,
        output_path,
        min_chars=321,
    )

    assert result is approval
    assert calls == [
        ("extract_text_from_pdf", pdf_path),
        ("ensure_text_pdf", "raw pdf text", 321),
        ("parse_material_from_text", "normalized", str(pdf_path)),
        ("load_context", context_path),
        ("build_approval_request", material, context),
        ("render_docx", approval, template_path, output_path),
    ]
