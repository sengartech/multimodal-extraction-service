from scope_modeler.eval.harness import EvalReport, evaluate_scope
from scope_modeler.models import (
    CaptureType,
    ClarifyingQuestion,
    GapSeverity,
    Modality,
    Provenance,
    ScopeBrief,
    SourceCapture,
    Task,
    TaskCategory,
    VersionedField,
)


def test_evaluate_scope_returns_eval_report():
    report = evaluate_scope(scope_fixture(), "memory://scope.json")

    assert isinstance(report, EvalReport)
    assert report.total_assertions >= 10
    assert report.field_type_metrics


def test_pricing_not_ready_assertion_passes_when_pricing_ready_false():
    report = evaluate_scope(scope_fixture(), "memory://scope.json")
    result = next(
        item for item in report.assertion_results if item.assertion_id == "pricing_not_ready"
    )

    assert result.status == "pass"


def test_missing_shower_task_causes_failure():
    scope = scope_fixture(include_shower=False)
    report = evaluate_scope(scope, "memory://scope.json")
    shower_result = next(
        item for item in report.assertion_results if item.assertion_id == "task_shower_installation"
    )

    assert shower_result.status == "fail"


def test_field_type_metrics_are_produced():
    report = evaluate_scope(scope_fixture(), "memory://scope.json")

    assert {metric.field_type for metric in report.field_type_metrics}
    assert all(metric.total_assertions > 0 for metric in report.field_type_metrics)


def scope_fixture(include_shower: bool = True) -> ScopeBrief:
    tasks = [
        task("task_wall", "Build 2 m non-full-height placo partition wall"),
        task("task_opening", "Create wall opening for access"),
        task("task_drainage", "Connect 100 mm drainage"),
        task("task_heater", "Install water heater"),
    ]
    if include_shower:
        tasks.insert(0, task("task_shower", "Install two staff showers"))

    return ScopeBrief(
        job_id="job-001",
        source_captures=[
            SourceCapture(
                capture_id="text_note_001",
                capture_type=CaptureType.CONTRACTOR_NOTE,
                modality=Modality.TEXT,
            )
        ],
        title=field("Create two staff showers"),
        description=field(
            "Install two staff showers with 2 m non-full-height placo partition, wall opening, "
            "100 mm drainage, and water heater."
        ),
        site_context=VersionedField[str | None](
            value="Existing finished space with access constraints.",
            confidence=0.8,
            provenance=[provenance()],
        ),
        tasks=tasks,
        materials=[
            material("mat_placo", "Placo partition boards"),
            material("mat_heater", "Water heater"),
        ],
        clarifying_questions=[
            ClarifyingQuestion(
                question="Confirm wall length and location.",
                severity=GapSeverity.MUST_HAVE,
                reason="Wall location affects pricing.",
                related_task_ids=["task_wall"],
                rank=1,
            ),
            ClarifyingQuestion(
                question="Confirm shower waterproofing and fixtures.",
                severity=GapSeverity.MUST_HAVE,
                reason="Waterproofing and fixtures affect pricing.",
                related_task_ids=["task_shower"],
                rank=2,
            ),
            ClarifyingQuestion(
                question="Confirm water heater capacity and electrical requirements.",
                severity=GapSeverity.MUST_HAVE,
                reason="Capacity affects pricing.",
                related_task_ids=["task_heater"],
                rank=3,
            ),
        ],
    )


def task(task_id: str, name: str) -> Task:
    return Task(
        task_id=task_id,
        category=TaskCategory.GENERAL,
        name=field(name),
        point_a=field("Existing state"),
        point_b=field("Completed state"),
        step_number=1,
        confidence=0.9,
        provenance=[provenance()],
    )


def material(material_id: str, name: str):
    from scope_modeler.models import Material

    return Material(
        material_id=material_id,
        name=field(name),
        estimated_quantity=VersionedField[float](
            value=1.0,
            confidence=0.7,
            provenance=[provenance()],
        ),
        unit="lot",
    )


def field(value: str) -> VersionedField[str]:
    return VersionedField[str](
        value=value,
        confidence=0.9,
        provenance=[provenance()],
    )


def provenance() -> Provenance:
    return Provenance(
        modality=Modality.FUSION,
        capture_id="fusion",
        extractor="test",
        confidence=0.9,
    )
