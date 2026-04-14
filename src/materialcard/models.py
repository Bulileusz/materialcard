"""Pydantic models for materialcard."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MaterialData(BaseModel):
    """Parsed material data."""

    source_path: Optional[str] = None
    raw_text: Optional[str] = None
    material_type: str
    description: str
    attachments: list[str] = Field(default_factory=list)


class ApprovalContext(BaseModel):
    """Context required to build approval requests."""

    template_variant: Optional[str] = None  # TODO: define template variants
    output_dir: Optional[str] = None  # TODO: define output directory
    investor_name: str
    project_title: str
    contractor_name: str
    manufacturer: str
    estimated_quantity: str
    planned_delivery_date: str
    planned_installation_date: str
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
    attachments_text: str

    prepared_by_name: str
    prepared_by_role: str
