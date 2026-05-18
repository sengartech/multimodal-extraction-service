"""Shared extractor contracts and typed partial results."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.inputs import InputCapture
from scope_modeler.models import (
    ClarifyingQuestion,
    Material,
    Modality,
    Provenance,
    Task,
    VersionedField,
)

ObservationValue = str | float | int | bool | None


class ExtractedObservation(BaseModel):
    """Single low-level fact or signal extracted from one capture."""

    model_config = ConfigDict(extra="forbid")

    label: str
    value: ObservationValue
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: Provenance
    notes: str | None = None


class ExtractorResult(BaseModel):
    """Structured partial evidence emitted by one modality extractor."""

    model_config = ConfigDict(extra="forbid")

    capture_id: str
    extractor_name: str
    modality: Modality
    observations: list[ExtractedObservation] = Field(default_factory=list)
    candidate_tasks: list[Task] = Field(default_factory=list)
    candidate_materials: list[Material] = Field(default_factory=list)
    assumptions: list[VersionedField[str]] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_output: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class BaseExtractor(Protocol):
    """Minimal strategy protocol for modality-specific extractors."""

    extractor_name: str
    supported_modalities: tuple[Modality, ...]

    def extract(self, capture: InputCapture) -> ExtractorResult:
        """Extract structured partial evidence from one input capture."""
