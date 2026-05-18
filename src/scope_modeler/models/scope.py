"""Core Pydantic v2 schema for renovation scope briefs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from scope_modeler.models.enums import (
    CaptureType,
    GapSeverity,
    Modality,
    PricingReadinessStatus,
    TaskCategory,
)
from scope_modeler.models.provenance import Provenance
from scope_modeler.models.versioned import VersionedField


class SourceCapture(BaseModel):
    """A raw or derived input available to extractors."""

    model_config = ConfigDict(extra="forbid")

    capture_id: str
    capture_type: CaptureType
    modality: Modality
    path: str | None = None
    description: str | None = None
    language: str | None = None


class Task(BaseModel):
    """Ordered unit of renovation work."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    category: TaskCategory
    name: VersionedField[str]
    point_a: VersionedField[str]
    point_b: VersionedField[str]
    step_number: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: list[Provenance] = Field(default_factory=list)


class Material(BaseModel):
    """Material line item with estimated quantity."""

    model_config = ConfigDict(extra="forbid")

    material_id: str
    name: VersionedField[str]
    estimated_quantity: VersionedField[float] = Field(
        description="Estimated material quantity in the provided unit."
    )
    unit: str
    related_task_ids: list[str] = Field(default_factory=list)


class ClarifyingQuestion(BaseModel):
    """Question needed to resolve gaps before pricing or execution."""

    model_config = ConfigDict(extra="forbid")

    question: str
    severity: GapSeverity
    reason: str
    related_task_ids: list[str] = Field(default_factory=list)
    rank: int = Field(ge=1)


class PricingReadinessCriteria(BaseModel):
    """Explicit criteria used to decide whether a scope can be priced."""

    model_config = ConfigDict(extra="forbid")

    title_exists: bool
    description_exists: bool
    has_tasks: bool
    no_must_have_questions: bool
    average_task_confidence_at_least_070: bool
    no_unresolved_critical_conflicts: bool


class PricingReadiness(BaseModel):
    """Computed pricing gate result and supporting reasons."""

    model_config = ConfigDict(extra="forbid")

    pricing_ready: bool
    status: PricingReadinessStatus
    criteria: PricingReadinessCriteria
    blocking_reasons: list[str] = Field(default_factory=list)
    average_task_confidence: float = Field(ge=0.0, le=1.0)


class ScopeBrief(BaseModel):
    """Typed scope brief produced by multimodal extraction and fusion."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    job_id: str
    schema_version: str = "0.1.0"
    source_captures: list[SourceCapture] = Field(default_factory=list)
    title: VersionedField[str]
    description: VersionedField[str]
    site_context: VersionedField[str | None] = Field(
        default_factory=lambda: VersionedField[str | None](
            value=None,
            confidence=0.0,
        )
    )
    tasks: list[Task] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)
    assumptions: list[VersionedField[str]] = Field(default_factory=list)
    exclusions: list[VersionedField[str]] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    unresolved_critical_conflicts: list[str] = Field(default_factory=list)
    pricing_readiness: PricingReadiness | None = None

    @model_validator(mode="after")
    def compute_pricing_readiness(self) -> "ScopeBrief":
        # Normalize ordering at the schema boundary so pricing receives deterministic output.
        self.tasks.sort(key=lambda task: task.step_number)
        self.clarifying_questions.sort(key=lambda question: question.rank)
        object.__setattr__(self, "pricing_readiness", self.build_pricing_readiness())
        return self

    @computed_field
    @property
    def ordered_task_ids(self) -> list[str]:
        return [task.task_id for task in self.tasks]

    def build_pricing_readiness(self) -> PricingReadiness:
        average_task_confidence = (
            sum(task.confidence for task in self.tasks) / len(self.tasks) if self.tasks else 0.0
        )
        criteria = PricingReadinessCriteria(
            title_exists=bool(self.title.value.strip()),
            description_exists=bool(self.description.value.strip()),
            has_tasks=bool(self.tasks),
            no_must_have_questions=not any(
                question.severity == GapSeverity.MUST_HAVE
                for question in self.clarifying_questions
            ),
            average_task_confidence_at_least_070=average_task_confidence >= 0.70,
            no_unresolved_critical_conflicts=not self.unresolved_critical_conflicts,
        )

        blocking_reasons: list[str] = []
        if not criteria.title_exists:
            blocking_reasons.append("title_missing")
        if not criteria.description_exists:
            blocking_reasons.append("description_missing")
        if not criteria.has_tasks:
            blocking_reasons.append("tasks_missing")
        if not criteria.no_must_have_questions:
            blocking_reasons.append("must_have_clarifying_questions")
        if not criteria.average_task_confidence_at_least_070:
            blocking_reasons.append("average_task_confidence_below_0.70")
        if not criteria.no_unresolved_critical_conflicts:
            blocking_reasons.append("unresolved_critical_conflicts")

        pricing_ready = not blocking_reasons
        status = PricingReadinessStatus.READY if pricing_ready else PricingReadinessStatus.NOT_READY
        
        return PricingReadiness(
            pricing_ready=pricing_ready,
            status=status,
            criteria=criteria,
            blocking_reasons=blocking_reasons,
            average_task_confidence=average_task_confidence,
        )
