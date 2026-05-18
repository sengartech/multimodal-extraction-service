"""Generic LLM-backed text extractor for construction notes."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.extractors.base import ExtractedObservation, ExtractorResult, ObservationValue
from scope_modeler.inputs import InputCapture
from scope_modeler.models import (
    ClarifyingQuestion,
    GapSeverity,
    Material,
    Modality,
    Provenance,
    Task,
    TaskCategory,
    VersionedField,
)


class DraftObservation(BaseModel):
    """Model-client draft observation before conversion to extractor contracts."""

    model_config = ConfigDict(extra="forbid")

    label: str
    value: ObservationValue
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None
    evidence_quote: str | None = None


class DraftTask(BaseModel):
    """Model-client draft task before conversion to the core schema."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    category: TaskCategory = TaskCategory.GENERAL
    name: str
    point_a: str
    point_b: str
    step_number: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)


class DraftMaterial(BaseModel):
    """Model-client draft material estimate before conversion to the core schema."""

    model_config = ConfigDict(extra="forbid")

    material_id: str
    name: str
    estimated_quantity: float = Field(ge=0.0)
    unit: str
    related_task_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class DraftQuestion(BaseModel):
    """Model-client draft clarifying question before conversion to the core schema."""

    model_config = ConfigDict(extra="forbid")

    question: str
    severity: GapSeverity
    reason: str
    related_task_ids: list[str] = Field(default_factory=list)
    rank: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)


class TextExtractionDraft(BaseModel):
    """Structured draft returned by a text model client."""

    model_config = ConfigDict(extra="forbid")

    observations: list[DraftObservation] = Field(default_factory=list)
    tasks: list[DraftTask] = Field(default_factory=list)
    materials: list[DraftMaterial] = Field(default_factory=list)
    assumptions: list[DraftObservation] = Field(default_factory=list)
    clarifying_questions: list[DraftQuestion] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_output: dict[str, object] = Field(default_factory=dict)


class TextModelClient(Protocol):
    """Client boundary for whatever text model produces the structured draft."""

    def extract_construction_scope(
        self,
        text: str,
        language: str | None,
    ) -> TextExtractionDraft:
        """Return a generic construction-scope draft for the provided text note."""


class LLMTextExtractor:
    """Text extractor that maps model-client drafts into shared extractor contracts."""

    extractor_name = "llm_text_extractor_v1"
    supported_modalities = (Modality.TEXT,)

    def __init__(self, model_client: TextModelClient) -> None:
        self.model_client = model_client

    def extract(self, capture: InputCapture) -> ExtractorResult:
        if capture.modality != Modality.TEXT:
            raise ValueError(
                f"{self.extractor_name} only supports text captures, got {capture.modality!s}"
            )

        note_text = Path(capture.path).read_text(encoding="utf-8")
        draft = self.model_client.extract_construction_scope(note_text, capture.language)
        return self._map_draft(capture, draft)

    def _map_draft(self, capture: InputCapture, draft: TextExtractionDraft) -> ExtractorResult:
        return ExtractorResult(
            capture_id=capture.capture_id,
            extractor_name=self.extractor_name,
            modality=Modality.TEXT,
            observations=[
                ExtractedObservation(
                    label=observation.label,
                    value=observation.value,
                    confidence=observation.confidence,
                    provenance=self._provenance(capture, observation.confidence),
                    notes=observation.notes or observation.evidence_quote,
                )
                for observation in draft.observations
            ],
            candidate_tasks=[
                Task(
                    task_id=task.task_id,
                    category=task.category,
                    name=self._versioned_text(capture, task.name, task.confidence),
                    point_a=self._versioned_text(capture, task.point_a, task.confidence),
                    point_b=self._versioned_text(capture, task.point_b, task.confidence),
                    step_number=task.step_number,
                    confidence=task.confidence,
                    provenance=[self._provenance(capture, task.confidence)],
                )
                for task in draft.tasks
            ],
            candidate_materials=[
                Material(
                    material_id=material.material_id,
                    name=self._versioned_text(capture, material.name, material.confidence),
                    estimated_quantity=self._versioned_quantity(
                        capture,
                        material.estimated_quantity,
                        material.confidence,
                    ),
                    unit=material.unit,
                    related_task_ids=material.related_task_ids,
                )
                for material in draft.materials
            ],
            assumptions=[
                self._versioned_text(capture, str(assumption.value), assumption.confidence)
                for assumption in draft.assumptions
                if assumption.value is not None
            ],
            clarifying_questions=[
                ClarifyingQuestion(
                    question=question.question,
                    severity=question.severity,
                    reason=question.reason,
                    related_task_ids=question.related_task_ids,
                    rank=question.rank,
                )
                for question in draft.clarifying_questions
            ],
            confidence=draft.confidence,
            raw_output={
                "model_raw_output": draft.raw_output,
                "normalized_draft": draft.model_dump(mode="json"),
            },
        )

    def _provenance(self, capture: InputCapture, confidence: float) -> Provenance:
        return Provenance(
            modality=Modality.TEXT,
            capture_id=capture.capture_id,
            extractor=self.extractor_name,
            confidence=confidence,
        )

    def _versioned_text(
        self,
        capture: InputCapture,
        value: str,
        confidence: float,
    ) -> VersionedField[str]:
        return VersionedField[str](
            value=value,
            confidence=confidence,
            provenance=[self._provenance(capture, confidence)],
        )

    def _versioned_quantity(
        self,
        capture: InputCapture,
        value: float,
        confidence: float,
    ) -> VersionedField[float]:
        return VersionedField[float](
            value=value,
            confidence=confidence,
            provenance=[self._provenance(capture, confidence)],
        )
