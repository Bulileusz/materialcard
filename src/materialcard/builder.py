"""Builder for approval request data."""

from __future__ import annotations

from .models import ApprovalContext, ApprovalRequestData, MaterialData

ATTACHMENTS_PLACEHOLDER = "—"


def build_approval_request(
    material: MaterialData,
    ctx: ApprovalContext,
) -> ApprovalRequestData:
    """Build approval request data from parsed material and contextual metadata."""

    attachments = ctx.attachments or material.attachments
    attachments_text = _format_attachments_text(attachments)

    payload = {
        "investor_name": ctx.investor_name,
        "project_title": ctx.project_title,
        "contractor_name": ctx.contractor_name,
        "material_type": material.material_type,
        "manufacturer": ctx.manufacturer,
        "estimated_quantity": ctx.estimated_quantity,
        "description": material.description,
        "planned_delivery_date": ctx.planned_delivery_date,
        "planned_installation_date": ctx.planned_installation_date,
        "attachments": attachments,
        "attachments_text": attachments_text,
        "prepared_by_name": ctx.prepared_by_name,
        "prepared_by_role": ctx.prepared_by_role,
    }

    return ApprovalRequestData(**payload)



def _format_attachments_text(attachments: list[str]) -> str:
    if not attachments:
        return ATTACHMENTS_PLACEHOLDER
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(attachments, start=1))
