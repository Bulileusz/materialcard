"""Pydantic models for materialcard."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, computed_field


ATTACHMENTS_PLACEHOLDER = "\u2014"


def _format_attachments(attachments: list[str]) -> str:
    if not attachments:
        return ATTACHMENTS_PLACEHOLDER
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(attachments, start=1))


class MaterialData(BaseModel):
    """Parsed material data."""

    source_path: Optional[str] = None
    raw_text: Optional[str] = None
    material_type: str
    description: str
    attachments: list[str] = Field(default_factory=list)


class ApprovalContext(BaseModel):
    """Context required to build approval requests."""

    # Runtime/configuration hints. The current CLI still receives template/output paths separately.
    template_variant: Optional[str] = None
    output_dir: Optional[str] = None

    # Business/project data used to build the approval request.
    investor_name: str
    project_title: str
    contractor_name: str

    # Material approval metadata supplied from project context, not parsed from PDF.
    manufacturer: str
    estimated_quantity: str
    planned_delivery_date: str
    planned_installation_date: str

    # Submission metadata.
    prepared_by_name: str
    prepared_by_role: str
    attachments: list[str] = Field(default_factory=list)


class ApprovalRequestData(BaseModel):
    """Data required by the Wrocław MVP approval template."""

    investor_name: str
    project_title: str
    contractor_name: str

    material_type: str
    manufacturer: str
    estimated_quantity: str
    description: str

    planned_delivery_date: str
    planned_installation_date: str

    attachments: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def attachments_text(self) -> str:
        """Template-ready attachment list derived from structured attachments."""

        return _format_attachments(self.attachments)

    prepared_by_name: str
    prepared_by_role: str
