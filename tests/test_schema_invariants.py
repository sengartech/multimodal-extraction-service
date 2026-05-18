import pytest
from pydantic import ValidationError

from scope_modeler.models import (
    CaptureType,
    ClarifyingQuestion,
    GapSeverity,
    Modality,
    PricingReadinessStatus,
    Provenance,
    ScopeBrief,
    SourceCapture,
    Task,
    TaskCategory,
    VersionedField,
)


def provenance(confidence: float = 0.9) -> Provenance:
    return Provenance(
        modality=Modality.TEXT,
        capture_id="note-001",
        extractor="test",
        confidence=confidence,
    )


def field(value: str, confidence: float = 0.9) -> VersionedField[str]:
    return VersionedField[str](
        value=value,
        confidence=confidence,
        provenance=[provenance(confidence)],
    )


def task(task_id: str, step_number: int, confidence: float = 0.9) -> Task:
    return Task(
        task_id=task_id,
        category=TaskCategory.GENERAL,
        name=field(f"Task {task_id}", confidence),
        point_a=field("Existing condition", confidence),
        point_b=field("Finished condition", confidence),
        step_number=step_number,
        confidence=confidence,
        provenance=[provenance(confidence)],
    )


def minimal_scope(**overrides) -> ScopeBrief:
    data = {
        "job_id": "job-001",
        "source_captures": [
            SourceCapture(
                capture_id="note-001",
                capture_type=CaptureType.CONTRACTOR_NOTE,
                modality=Modality.TEXT,
                language="fr",
            )
        ],
        "title": field("Renovation scope"),
        "description": field("Create a generic renovation work package."),
        "tasks": [task("task-001", 1, 0.9)],
    }
    data.update(overrides)
    return ScopeBrief(**data)


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        provenance(1.1)

    with pytest.raises(ValidationError):
        field("invalid", -0.1)

    with pytest.raises(ValidationError):
        task("task-001", 1, 1.01)


def test_must_have_clarifying_question_makes_pricing_not_ready():
    scope = minimal_scope(
        clarifying_questions=[
            ClarifyingQuestion(
                question="Quelle est la surface exacte a traiter ?",
                severity=GapSeverity.MUST_HAVE,
                reason="Quantity is required before pricing.",
                related_task_ids=["task-001"],
                rank=1,
            )
        ]
    )

    assert scope.pricing_readiness is not None
    assert scope.pricing_readiness.pricing_ready is False
    assert scope.pricing_readiness.status == PricingReadinessStatus.NOT_READY
    assert "must_have_clarifying_questions" in scope.pricing_readiness.blocking_reasons


def test_valid_minimal_scope_with_high_confidence_task_can_become_ready():
    scope = minimal_scope()

    assert scope.pricing_readiness is not None
    assert scope.pricing_readiness.pricing_ready is True
    assert scope.pricing_readiness.status == PricingReadinessStatus.READY
    assert scope.pricing_readiness.blocking_reasons == []
    assert scope.pricing_readiness.criteria.average_task_confidence_at_least_070 is True


def test_task_ordering_is_stable():
    scope = minimal_scope(
        tasks=[
            task("task-003", 3, 0.9),
            task("task-001", 1, 0.9),
            task("task-002", 2, 0.9),
        ]
    )

    assert scope.ordered_task_ids == ["task-001", "task-002", "task-003"]
    assert [item.step_number for item in scope.tasks] == [1, 2, 3]
