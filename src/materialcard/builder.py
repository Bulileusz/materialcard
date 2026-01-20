"""Builder for approval request data."""

from __future__ import annotations

from .models import ApprovalContext, ApprovalRequestData, MaterialData


def build_approval_request(
    material: MaterialData,
    ctx: ApprovalContext,
) -> ApprovalRequestData:
    """Build approval request data."""

    return ApprovalRequestData(material=material, context=ctx)
