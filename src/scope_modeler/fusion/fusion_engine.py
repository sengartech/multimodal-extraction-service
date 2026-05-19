"""LLM-assisted fusion from extractor evidence into a final ScopeBrief."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.extractors import ExtractorResult
from scope_modeler.models import (
    ClarifyingQuestion,
    GapSeverity,
    Material,
    Modality,
    Provenance,
    ScopeBrief,
    SourceCapture,
    Task,
    TaskCategory,
    VersionedField,
)


class EvidenceItem(BaseModel):
    """Normalized evidence item packaged for fusion."""

    model_config = ConfigDict(extra="forbid")

    source: str
    label: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: list[Provenance] = Field(default_factory=list)
    notes: str | None = None


class EvidenceBundle(BaseModel):
    """Deterministic evidence package sent to the fusion model."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    source_captures: list[SourceCapture] = Field(default_factory=list)
    observations: list[EvidenceItem] = Field(default_factory=list)
    candidate_tasks: list[EvidenceItem] = Field(default_factory=list)
    candidate_materials: list[EvidenceItem] = Field(default_factory=list)
    assumptions: list[EvidenceItem] = Field(default_factory=list)
    clarifying_questions: list[EvidenceItem] = Field(default_factory=list)
    provenance_summary: list[str] = Field(default_factory=list)
    modality_summaries: dict[str, int] = Field(default_factory=dict)
    unresolved_conflicts: list[str] = Field(default_factory=list)


class FusionDraftTask(BaseModel):
    """Final task proposed by fusion."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    category: TaskCategory
    name: str
    point_a: str
    point_b: str
    step_number: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_capture_ids: list[str] = Field(default_factory=list)


class FusionDraftMaterial(BaseModel):
    """Final material proposed by fusion."""

    model_config = ConfigDict(extra="forbid")

    material_id: str
    name: str
    estimated_quantity: float = Field(ge=0.0)
    unit: str
    related_task_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_capture_ids: list[str] = Field(default_factory=list)


class FusionDraftQuestion(BaseModel):
    """Final clarifying question proposed by fusion."""

    model_config = ConfigDict(extra="forbid")

    question: str
    severity: GapSeverity
    reason: str
    related_task_ids: list[str] = Field(default_factory=list)
    rank: int = Field(ge=1)


class FusionDraft(BaseModel):
    """Structured model draft for the final scope brief."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    site_context: str | None = None
    tasks: list[FusionDraftTask] = Field(default_factory=list)
    materials: list[FusionDraftMaterial] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    clarifying_questions: list[FusionDraftQuestion] = Field(default_factory=list)
    unresolved_critical_conflicts: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class OpenAIFusionResponse(BaseModel):
    """Structured OpenAI response shape with required collection fields."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    site_context: str | None
    tasks: list[FusionDraftTask]
    materials: list[FusionDraftMaterial]
    assumptions: list[str]
    exclusions: list[str]
    clarifying_questions: list[FusionDraftQuestion]
    unresolved_critical_conflicts: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class FusionModelClient(Protocol):
    """Model-client boundary for cross-modal synthesis."""

    def synthesize_scope(self, evidence_bundle: EvidenceBundle) -> FusionDraft:
        """Synthesize a final scope draft from normalized evidence."""


class OpenAIFusionModelClient:
    """OpenAI-backed fusion client using structured JSON output."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required to use OpenAIFusionModelClient. "
                "Unit tests should use a fake FusionModelClient."
            )
        self.model = model or os.getenv("FUSION_MODEL", "gpt-5.4")

    def synthesize_scope(self, evidence_bundle: EvidenceBundle) -> FusionDraft:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        schema = _to_openai_strict_json_schema(OpenAIFusionResponse.model_json_schema())
        prompt = (
            "Synthesize a final renovation/construction scope from the normalized evidence bundle "
            "only. Return only JSON matching the schema. Include every required field. Use [] for "
            "empty arrays and null for unknown nullable values. Do not include extra keys outside "
            "the schema. Prefer explicit contractor text/audio for requested transformations. Use "
            "photos mainly for existing-state context, constraints, and pricing risks. Use drawing "
            "evidence for layout and dimension uncertainty. Do not convert photo-only "
            "existing-condition observations into requested work unless another modality supports "
            "it. Do not invent precise quantities. Preserve unknowns as assumptions or clarifying "
            "questions. Rank must-have pricing blockers first and mark unknowns explicitly."
        )
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_text",
                            "text": json.dumps(
                                evidence_bundle.model_dump(mode="json"),
                                ensure_ascii=False,
                            ),
                        },
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "fusion_draft",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise RuntimeError("OpenAI fusion response did not include output_text JSON.")
        response_draft = OpenAIFusionResponse.model_validate(json.loads(output_text))
        return FusionDraft.model_validate(response_draft.model_dump(mode="python"))


class FusionEngine:
    """Fuse extractor results into a final typed ScopeBrief."""

    extractor_name = "fusion_engine_v1"

    def __init__(self, fusion_model_client: FusionModelClient) -> None:
        self.fusion_model_client = fusion_model_client

    def fuse(
        self,
        job_id: str,
        source_captures: list[SourceCapture],
        extractor_results: list[ExtractorResult],
    ) -> ScopeBrief:
        evidence_bundle = build_evidence_bundle(job_id, source_captures, extractor_results)
        draft = self.fusion_model_client.synthesize_scope(evidence_bundle)
        return self._map_draft_to_scope(job_id, source_captures, draft)

    def _map_draft_to_scope(
        self,
        job_id: str,
        source_captures: list[SourceCapture],
        draft: FusionDraft,
    ) -> ScopeBrief:
        return ScopeBrief(
            job_id=job_id,
            source_captures=source_captures,
            title=self._versioned_text(draft.title, draft.confidence, []),
            description=self._versioned_text(draft.description, draft.confidence, []),
            site_context=self._versioned_optional_text(draft.site_context, draft.confidence, []),
            tasks=[
                Task(
                    task_id=task.task_id,
                    category=task.category,
                    name=self._versioned_text(
                        task.name,
                        task.confidence,
                        self._supporting_provenance(task.supporting_capture_ids, source_captures),
                    ),
                    point_a=self._versioned_text(
                        task.point_a,
                        task.confidence,
                        self._supporting_provenance(task.supporting_capture_ids, source_captures),
                    ),
                    point_b=self._versioned_text(
                        task.point_b,
                        task.confidence,
                        self._supporting_provenance(task.supporting_capture_ids, source_captures),
                    ),
                    step_number=task.step_number,
                    confidence=task.confidence,
                    provenance=[
                        self._fusion_provenance(task.confidence),
                        *self._supporting_provenance(
                            task.supporting_capture_ids,
                            source_captures,
                        ),
                    ],
                )
                for task in draft.tasks
            ],
            materials=[
                Material(
                    material_id=material.material_id,
                    name=self._versioned_text(
                        material.name,
                        material.confidence,
                        self._supporting_provenance(
                            material.supporting_capture_ids,
                            source_captures,
                        ),
                    ),
                    estimated_quantity=VersionedField[float](
                        value=material.estimated_quantity,
                        confidence=material.confidence,
                        provenance=[
                            self._fusion_provenance(material.confidence),
                            *self._supporting_provenance(
                                material.supporting_capture_ids,
                                source_captures,
                            ),
                        ],
                    ),
                    unit=material.unit,
                    related_task_ids=material.related_task_ids,
                )
                for material in draft.materials
            ],
            assumptions=[
                self._versioned_text(assumption, draft.confidence, [])
                for assumption in draft.assumptions
            ],
            exclusions=[
                self._versioned_text(exclusion, draft.confidence, [])
                for exclusion in draft.exclusions
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
            unresolved_critical_conflicts=draft.unresolved_critical_conflicts,
        )

    def _versioned_text(
        self,
        value: str,
        confidence: float,
        supporting_provenance: list[Provenance],
    ) -> VersionedField[str]:
        return VersionedField[str](
            value=value,
            confidence=confidence,
            provenance=[self._fusion_provenance(confidence), *supporting_provenance],
        )

    def _versioned_optional_text(
        self,
        value: str | None,
        confidence: float,
        supporting_provenance: list[Provenance],
    ) -> VersionedField[str | None]:
        return VersionedField[str | None](
            value=value,
            confidence=confidence,
            provenance=[self._fusion_provenance(confidence), *supporting_provenance],
        )

    def _fusion_provenance(self, confidence: float) -> Provenance:
        return Provenance(
            modality=Modality.FUSION,
            capture_id="fusion",
            extractor=self.extractor_name,
            confidence=confidence,
        )

    def _supporting_provenance(
        self,
        capture_ids: list[str],
        source_captures: list[SourceCapture],
    ) -> list[Provenance]:
        capture_by_id = {capture.capture_id: capture for capture in source_captures}
        return [
            Provenance(
                modality=capture_by_id[capture_id].modality,
                capture_id=capture_id,
                extractor="supporting_evidence",
                confidence=1.0,
            )
            for capture_id in capture_ids
            if capture_id in capture_by_id
        ]


def build_evidence_bundle(
    job_id: str,
    source_captures: list[SourceCapture],
    extractor_results: list[ExtractorResult],
) -> EvidenceBundle:
    modality_counts: dict[str, int] = {}
    observations: list[EvidenceItem] = []
    candidate_tasks: list[EvidenceItem] = []
    candidate_materials: list[EvidenceItem] = []
    assumptions: list[EvidenceItem] = []
    clarifying_questions: list[EvidenceItem] = []
    provenance_summary: list[str] = []

    for result in extractor_results:
        modality_counts[result.modality.value] = modality_counts.get(result.modality.value, 0) + 1
        provenance_summary.append(
            f"{result.extractor_name}:{result.capture_id}:{result.modality.value}:{result.confidence:.2f}"
        )
        observations.extend(
            EvidenceItem(
                source="observation",
                label=observation.label,
                value=observation.value,
                confidence=observation.confidence,
                provenance=[observation.provenance],
                notes=observation.notes,
            )
            for observation in result.observations
        )
        candidate_tasks.extend(
            EvidenceItem(
                source="candidate_task",
                label=task.task_id,
                value={
                    "name": task.name.value,
                    "category": task.category.value,
                    "point_a": task.point_a.value,
                    "point_b": task.point_b.value,
                    "step_number": task.step_number,
                },
                confidence=task.confidence,
                provenance=task.provenance,
            )
            for task in result.candidate_tasks
        )
        candidate_materials.extend(
            EvidenceItem(
                source="candidate_material",
                label=material.material_id,
                value={
                    "name": material.name.value,
                    "estimated_quantity": material.estimated_quantity.value,
                    "unit": material.unit,
                    "related_task_ids": material.related_task_ids,
                },
                confidence=material.name.confidence,
                provenance=material.name.provenance,
            )
            for material in result.candidate_materials
        )
        assumptions.extend(
            EvidenceItem(
                source="assumption",
                label="assumption",
                value=assumption.value,
                confidence=assumption.confidence,
                provenance=assumption.provenance,
            )
            for assumption in result.assumptions
        )
        clarifying_questions.extend(
            EvidenceItem(
                source="clarifying_question",
                label=question.severity.value,
                value={
                    "question": question.question,
                    "reason": question.reason,
                    "related_task_ids": question.related_task_ids,
                    "rank": question.rank,
                },
                confidence=result.confidence,
                provenance=[
                    Provenance(
                        modality=result.modality,
                        capture_id=result.capture_id,
                        extractor=result.extractor_name,
                        confidence=result.confidence,
                    )
                ],
            )
            for question in result.clarifying_questions
        )

    return EvidenceBundle(
        job_id=job_id,
        source_captures=source_captures,
        observations=observations,
        candidate_tasks=candidate_tasks,
        candidate_materials=candidate_materials,
        assumptions=assumptions,
        clarifying_questions=clarifying_questions,
        provenance_summary=provenance_summary,
        modality_summaries=modality_counts,
    )


def _to_openai_strict_json_schema(schema: dict[str, object]) -> dict[str, object]:
    strict_schema = dict(schema)
    _make_schema_node_strict(strict_schema)
    return strict_schema


def _make_schema_node_strict(node: object) -> None:
    if isinstance(node, dict):
        for keyword in ("default", "title", "examples", "description"):
            node.pop(keyword, None)

        if "$ref" in node:
            ref = node["$ref"]
            node.clear()
            node["$ref"] = ref
            return

        properties = node.get("properties")
        if isinstance(properties, dict):
            node["required"] = list(properties.keys())
            node["additionalProperties"] = False

        for key in ("$defs", "properties"):
            child_mapping = node.get(key)
            if isinstance(child_mapping, dict):
                for child in child_mapping.values():
                    _make_schema_node_strict(child)

        items = node.get("items")
        if items is not None:
            _make_schema_node_strict(items)

        for key in ("anyOf", "oneOf", "allOf"):
            variants = node.get(key)
            if isinstance(variants, list):
                for variant in variants:
                    _make_schema_node_strict(variant)
    elif isinstance(node, list):
        for item in node:
            _make_schema_node_strict(item)
