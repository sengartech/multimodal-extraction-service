"""Generic LLM-backed text extractor for construction notes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.extractors.base import ExtractedObservation, ExtractorResult, ObservationValue
from scope_modeler.inputs import InputCapture
from scope_modeler.llm.openai_client import OpenAIStructuredClient
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


class OpenAITextExtractionResponse(BaseModel):
    """Strict OpenAI response shape for text extraction."""

    model_config = ConfigDict(extra="forbid")

    observations: list[DraftObservation]
    tasks: list[DraftTask]
    materials: list[DraftMaterial]
    assumptions: list[DraftObservation]
    clarifying_questions: list[DraftQuestion]
    confidence: float = Field(ge=0.0, le=1.0)


class TextModelClient(Protocol):
    """Client boundary for whatever text model produces the structured draft."""

    def extract_construction_scope(
        self,
        text: str,
        language: str | None,
    ) -> TextExtractionDraft:
        """Return a generic construction-scope draft for the provided text note."""


class OpenAITextModelClient:
    """OpenAI-backed text model client for contractor construction notes."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or os.getenv("TEXT_MODEL", "gpt-5.4")
        self.client = OpenAIStructuredClient(api_key=api_key)

    def extract_construction_scope(
        self,
        text: str,
        language: str | None,
    ) -> TextExtractionDraft:
        response = self.client.run_text(
            model=self.model,
            schema_name="text_extraction_draft",
            system_prompt=(
                "You extract structured renovation/construction scope evidence from "
                "contractor text notes."
            ),
            user_prompt=(
                "Original contractor note:\n"
                f"{text}\n\n"
                f"Language: {language or 'unknown'}\n\n"
                "Return only JSON matching the schema. Include every required field. "
                "Use [] for empty arrays. Do not include extra keys outside the schema. "
                "Extract observations, tasks, materials, assumptions, and clarifying questions. "
                "The raw contractor note may be in French or another language, but the internal "
                "canonical extraction output must be in English. Use English snake_case labels for "
                "observations. Use English task names, point_a, point_b, material names, "
                "assumptions, and clarifying questions. Preserve original-language construction "
                "terms only when useful as domain terms or in evidence_quote, such as placo, "
                "évacuation, and chauffe-eau. Normalize quantities where possible: for example, "
                "\"2 mètres\" should become numeric 2.0 with label partition_wall_height_m, and "
                "\"évacuation 100\" should become drainage_diameter_mm = 100 when supported. "
                "For assumptions, use a human-readable English sentence in notes. "
                "Do not use boolean-only assumption values unless the label and notes clearly explain the assumption."
                "Do not translate capture IDs or enum values. Do not invent precise quantities "
                "not present in the text. Mark missing pricing inputs as clarifying questions."
            ),
            response_model=OpenAITextExtractionResponse,
        )
        return TextExtractionDraft(
            **response.model_dump(mode="python"),
            raw_output={"provider": "openai", "model": self.model},
        )


def map_text_draft_to_extractor_result(
    *,
    capture: InputCapture,
    draft: TextExtractionDraft,
    extractor_name: str,
    modality: Modality,
    raw_output: dict[str, object] | None = None,
) -> ExtractorResult:
    """Map a text-model draft into the shared extractor result schema."""

    return ExtractorResult(
        capture_id=capture.capture_id,
        extractor_name=extractor_name,
        modality=modality,
        observations=[
            ExtractedObservation(
                label=observation.label,
                value=observation.value,
                confidence=observation.confidence,
                provenance=_provenance(capture, extractor_name, modality, observation.confidence),
                notes=observation.notes or observation.evidence_quote,
            )
            for observation in draft.observations
        ],
        candidate_tasks=[
            Task(
                task_id=task.task_id,
                category=task.category,
                name=_versioned_text(capture, extractor_name, modality, task.name, task.confidence),
                point_a=_versioned_text(
                    capture,
                    extractor_name,
                    modality,
                    task.point_a,
                    task.confidence,
                ),
                point_b=_versioned_text(
                    capture,
                    extractor_name,
                    modality,
                    task.point_b,
                    task.confidence,
                ),
                step_number=task.step_number,
                confidence=task.confidence,
                provenance=[_provenance(capture, extractor_name, modality, task.confidence)],
            )
            for task in draft.tasks
        ],
        candidate_materials=[
            Material(
                material_id=material.material_id,
                name=_versioned_text(
                    capture,
                    extractor_name,
                    modality,
                    material.name,
                    material.confidence,
                ),
                estimated_quantity=_versioned_quantity(
                    capture,
                    extractor_name,
                    modality,
                    material.estimated_quantity,
                    material.confidence,
                ),
                unit=material.unit,
                related_task_ids=material.related_task_ids,
            )
            for material in draft.materials
        ],
        assumptions=[
            _versioned_text(
                capture,
                extractor_name,
                modality,
                _assumption_to_text(assumption),
                assumption.confidence,
            )
            for assumption in draft.assumptions
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
        raw_output=raw_output
        or {
            "model_raw_output": draft.raw_output,
            "normalized_draft": draft.model_dump(mode="json"),
        },
    )

def _assumption_to_text(assumption: DraftObservation) -> str:
    if assumption.notes:
        return assumption.notes
    if assumption.value is not None and not isinstance(assumption.value, bool):
        return str(assumption.value)
    return assumption.label.replace("_", " ")


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
        return map_text_draft_to_extractor_result(
            capture=capture,
            draft=draft,
            extractor_name=self.extractor_name,
            modality=Modality.TEXT,
        )


def _provenance(
    capture: InputCapture,
    extractor_name: str,
    modality: Modality,
    confidence: float,
) -> Provenance:
    return Provenance(
        modality=modality,
        capture_id=capture.capture_id,
        extractor=extractor_name,
        confidence=confidence,
    )


def _versioned_text(
    capture: InputCapture,
    extractor_name: str,
    modality: Modality,
    value: str,
    confidence: float,
) -> VersionedField[str]:
    return VersionedField[str](
        value=value,
        confidence=confidence,
        provenance=[_provenance(capture, extractor_name, modality, confidence)],
    )


def _versioned_quantity(
    capture: InputCapture,
    extractor_name: str,
    modality: Modality,
    value: float,
    confidence: float,
) -> VersionedField[float]:
    return VersionedField[float](
        value=value,
        confidence=confidence,
        provenance=[_provenance(capture, extractor_name, modality, confidence)],
    )
