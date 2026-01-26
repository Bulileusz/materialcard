"""Builder for approval request data."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import ApprovalContext, ApprovalRequestData, MaterialData

ATTACHMENTS_PLACEHOLDER = "—"


def build_approval_request(
    material: MaterialData,
    ctx: ApprovalContext,
) -> ApprovalRequestData:
    """Build approval request data from parsed material and contextual metadata."""

    material_data = material.model_dump(exclude_none=True)
    context_data = _flatten_context(ctx)

    attachments = _resolve_attachments(context_data, material_data)
    attachments_text = _format_attachments_text(attachments)

    payload = {
        "investor_name": context_data.get("investor_name"),
        "project_title": context_data.get("project_title"),
        "contractor_name": context_data.get("contractor_name"),
        "material_type": material_data.get("material_type") or material_data.get("material_name"),
        "manufacturer": material_data.get("manufacturer"),
        "estimated_quantity": material_data.get("estimated_quantity"),
        "description": material_data.get("description"),
        "planned_delivery_date": context_data.get("planned_delivery_date"),
        "planned_installation_date": context_data.get("planned_installation_date"),
        "attachments": attachments,
        "attachments_text": attachments_text,
        "prepared_by_name": context_data.get("prepared_by_name"),
        "prepared_by_role": context_data.get("prepared_by_role"),
    }

    return ApprovalRequestData(**payload)


def _flatten_context(ctx: ApprovalContext) -> dict[str, Any]:
    """Merge ApprovalContext fields with metadata overrides."""

    data = ctx.model_dump(exclude_none=True)
    metadata = data.pop("metadata", None)
    flattened = {k: v for k, v in data.items() if v is not None}
    if isinstance(metadata, dict):
        flattened.update({k: v for k, v in metadata.items() if v is not None})
    return flattened


def _resolve_attachments(*sources: dict[str, Any]) -> list[str]:
    """Pick the first non-empty attachments sequence from provided sources."""

    for source in sources:
        if not source:
            continue
        normalized = _normalize_attachments(source.get("attachments"))
        if normalized:
            return normalized
    return []


def _normalize_attachments(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        iterable = [raw]
    elif isinstance(raw, dict):
        iterable = list(raw.values())
    elif isinstance(raw, Iterable):
        iterable = list(raw)
    else:
        iterable = [raw]

    normalized: list[str] = []
    for item in iterable:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _format_attachments_text(attachments: list[str]) -> str:
    if not attachments:
        return ATTACHMENTS_PLACEHOLDER
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(attachments, start=1))
