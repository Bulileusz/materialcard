"""Tests for approval request builder."""

from materialcard.builder import build_approval_request
from materialcard.models import ApprovalContext, MaterialData


def _make_material(*, attachments: list[str]) -> MaterialData:
    return MaterialData(
        material_type="Material",
        description="Desc",
        attachments=attachments,
    )


def _make_context(*, attachments: list[str]) -> ApprovalContext:
    return ApprovalContext(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        manufacturer="Manufacturer",
        estimated_quantity="10",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
        attachments=attachments,
    )


def test_build_approval_request_happy_path() -> None:
    material = _make_material(attachments=["Spec A"])
    context = _make_context(attachments=["Attachment 1", "Attachment 2"])

    result = build_approval_request(material, context)

    assert result.attachments == ["Attachment 1", "Attachment 2"]
    assert result.attachments_text == "1. Attachment 1\n2. Attachment 2"


def test_build_approval_request_empty_attachments_placeholder() -> None:
    material = _make_material(attachments=[])
    context = _make_context(attachments=[])

    result = build_approval_request(material, context)

    assert result.attachments == []
    assert result.attachments_text == "—"

