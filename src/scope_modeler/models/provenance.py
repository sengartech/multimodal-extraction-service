"""Provenance primitives for extracted and fused scope fields."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.models.enums import Modality


class Provenance(BaseModel):
    """Evidence trail for a field or model element."""

    model_config = ConfigDict(extra="forbid")

    modality: Modality
    capture_id: str
    extractor: str
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

