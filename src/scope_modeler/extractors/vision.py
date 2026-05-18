"""Generic vision extractor for construction and renovation site photos."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
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


class VisionObservation(BaseModel):
    """Visible fact or risk extracted from a site photo."""

    model_config = ConfigDict(extra="forbid")

    label: str
    value: ObservationValue
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class VisionDraftTask(BaseModel):
    """Draft task supported by visible evidence in a photo."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    category: TaskCategory = TaskCategory.GENERAL
    name: str
    point_a: str
    point_b: str
    step_number: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)


class VisionDraftMaterial(BaseModel):
    """Draft material estimate supported by visible evidence in a photo."""

    model_config = ConfigDict(extra="forbid")

    material_id: str
    name: str
    estimated_quantity: float = Field(ge=0.0)
    unit: str
    related_task_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class VisionDraftQuestion(BaseModel):
    """Clarifying question raised by ambiguous or incomplete photo evidence."""

    model_config = ConfigDict(extra="forbid")

    question: str
    severity: GapSeverity
    reason: str
    related_task_ids: list[str] = Field(default_factory=list)
    rank: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)


class VisionExtractionDraft(BaseModel):
    """Structured draft returned by a vision model client."""

    model_config = ConfigDict(extra="forbid")

    image_quality: str
    visible_elements: list[str] = Field(default_factory=list)
    unclear_regions: list[str] = Field(default_factory=list)
    observations: list[VisionObservation] = Field(default_factory=list)
    tasks: list[VisionDraftTask] = Field(default_factory=list)
    materials: list[VisionDraftMaterial] = Field(default_factory=list)
    clarifying_questions: list[VisionDraftQuestion] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_output: dict[str, object] = Field(default_factory=dict)


class VisionModelClient(Protocol):
    """Client boundary for a vision model provider."""

    def extract_from_image(
        self,
        image_path: Path,
        language_hint: str | None = None,
    ) -> VisionExtractionDraft:
        """Return structured construction-scope evidence from a site photo."""


class OpenAIVisionModelClient:
    """OpenAI-backed vision client using base64 image input and strict JSON."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required to use OpenAIVisionModelClient. "
                "Unit tests should use a fake VisionModelClient."
            )
        self.model = model or os.getenv("VISION_MODEL", "gpt-5.4")

    def extract_from_image(
        self,
        image_path: Path,
        language_hint: str | None = None,
    ) -> VisionExtractionDraft:
        from openai import OpenAI

        image_path = Path(image_path)
        data_url = _image_to_data_url(image_path)
        client = OpenAI(api_key=self.api_key)
        schema = VisionExtractionDraft.model_json_schema()
        prompt = (
            "Analyze this construction or renovation site photo. Return only JSON matching the "
            "provided schema. Be conservative: include candidate tasks and materials only when "
            "the image visibly supports them. Capture visible existing-state facts, uncertainty, "
            "image quality, unclear regions, pricing-relevant risks, and clarifying questions. "
            f"Language hint: {language_hint or 'unknown'}."
        )
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url, "detail": "auto"},
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "vision_extraction_draft",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise RuntimeError("OpenAI vision response did not include output_text JSON.")
        data = json.loads(output_text)
        draft = VisionExtractionDraft.model_validate(data)
        if not draft.raw_output:
            object.__setattr__(draft, "raw_output", {"provider": "openai", "model": self.model})
        return draft


class VisionExtractor:
    """Vision extractor that maps model-client drafts into shared extractor contracts."""

    extractor_name = "vision_extractor_v1"
    supported_modalities = (Modality.PHOTO,)

    def __init__(self, vision_model_client: VisionModelClient) -> None:
        self.vision_model_client = vision_model_client

    def extract(self, capture: InputCapture) -> ExtractorResult:
        if capture.modality != Modality.PHOTO:
            raise ValueError(
                f"{self.extractor_name} only supports photo captures, got {capture.modality!s}"
            )

        image_path = Path(capture.path)
        if not image_path.exists():
            raise FileNotFoundError(image_path)

        draft = self.vision_model_client.extract_from_image(image_path, capture.language)
        return ExtractorResult(
            capture_id=capture.capture_id,
            extractor_name=self.extractor_name,
            modality=Modality.PHOTO,
            observations=self._map_observations(capture, draft),
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

    def _map_observations(
        self,
        capture: InputCapture,
        draft: VisionExtractionDraft,
    ) -> list[ExtractedObservation]:
        observations = [
            ExtractedObservation(
                label="image_quality",
                value=draft.image_quality,
                confidence=draft.confidence,
                provenance=self._provenance(capture, draft.confidence),
            ),
            ExtractedObservation(
                label="visible_elements",
                value=", ".join(draft.visible_elements) if draft.visible_elements else None,
                confidence=draft.confidence,
                provenance=self._provenance(capture, draft.confidence),
            ),
            ExtractedObservation(
                label="unclear_regions",
                value=", ".join(draft.unclear_regions) if draft.unclear_regions else None,
                confidence=draft.confidence,
                provenance=self._provenance(capture, draft.confidence),
                notes="Regions the model could not inspect confidently.",
            ),
        ]
        observations.extend(
            ExtractedObservation(
                label=observation.label,
                value=observation.value,
                confidence=observation.confidence,
                provenance=self._provenance(capture, observation.confidence),
                notes=observation.notes,
            )
            for observation in draft.observations
        )
        return observations

    def _provenance(self, capture: InputCapture, confidence: float) -> Provenance:
        return Provenance(
            modality=Modality.PHOTO,
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


def _image_to_data_url(image_path: Path) -> str:
    media_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"
