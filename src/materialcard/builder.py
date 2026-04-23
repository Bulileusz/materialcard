"""Builder for approval request data."""

from __future__ import annotations

from .models import ApprovalContext, ApprovalRequestData, MaterialData


def build_approval_request(
    material: MaterialData,
    ctx: ApprovalContext,
) -> ApprovalRequestData:
    """Build approval request data from parsed material and contextual metadata."""

    attachments = _select_attachments(material=material, ctx=ctx)

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
        "prepared_by_name": ctx.prepared_by_name,
        "prepared_by_role": ctx.prepared_by_role,
    }

    return ApprovalRequestData(**payload)


def _select_attachments(
    *,
    material: MaterialData,
    ctx: ApprovalContext,
) -> list[str]:
    if ctx.attachments:
        return ctx.attachments
    return material.attachments
