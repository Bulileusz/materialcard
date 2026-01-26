"""Pydantic models for materialcard."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MaterialData(BaseModel):
    """Parsed material data."""

    source_path: Optional[str] = None
    raw_text: Optional[str] = None
    material_name: Optional[str] = None  # TODO: define actual name field
    description: Optional[str] = None  # TODO: define description field
    items: list[str] = Field(default_factory=list)  # TODO: define item schema


class ApprovalContext(BaseModel):
    """Context required to build approval requests."""

    template_variant: Optional[str] = None  # TODO: define template variants
    output_dir: Optional[str] = None  # TODO: define output directory
    metadata: dict[str, str] = Field(default_factory=dict)  # TODO: define metadata keys


class ApprovalRequestData(BaseModel):
    """Data required by the Wrocław MVP approval template."""

    investor_name: str
    project_title: str
    contractor_name: str

    material_type: str
    manufacturer: Optional[str] = None
    estimated_quantity: str
    description: Optional[str] = None

    planned_delivery_date: Optional[str] = None
    planned_installation_date: Optional[str] = None

    attachments: list[str] = Field(default_factory=list)
    attachments_text: str

    prepared_by_name: Optional[str] = None
    prepared_by_role: Optional[str] = None
