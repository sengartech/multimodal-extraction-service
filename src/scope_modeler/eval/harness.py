"""Deterministic assertion-based evaluation harness."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.models import ScopeBrief


class GroundTruthAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    field_type: str
    description: str
    expected: str
    required_terms: list[str]
    search_sections: list[str]
    must_be_absent: bool = False


class AssertionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    field_type: str
    status: Literal["pass", "fail", "partial"]
    expected: str
    actual: str
    notes: str | None = None


class FieldTypeMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_type: str
    total_assertions: int
    passed: int
    failed: int
    partial: int
    precision: float
    recall: float


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope_path: str
    total_assertions: int
    passed: int
    failed: int
    partial: int
    overall_precision: float
    overall_recall: float
    field_type_metrics: list[FieldTypeMetrics]
    assertion_results: list[AssertionResult]
    notes: str


GROUND_TRUTH_ASSERTIONS: list[GroundTruthAssertion] = [
    GroundTruthAssertion(
        assertion_id="task_shower_installation",
        field_type="tasks",
        description="Shower installation task present",
        expected="Scope includes installing/creating two staff showers.",
        required_terms=["shower", "two"],
        search_sections=["tasks"],
    ),
    GroundTruthAssertion(
        assertion_id="task_placo_partition",
        field_type="tasks",
        description="Placo partition wall task present",
        expected="Scope includes placo partition wall work.",
        required_terms=["placo", "partition"],
        search_sections=["description", "tasks", "materials"],
    ),
    GroundTruthAssertion(
        assertion_id="measurement_wall_height_2m",
        field_type="measurements",
        description="2m wall height present",
        expected="Scope preserves 2 m wall height.",
        required_terms=["2", "m"],
        search_sections=["description", "tasks", "materials", "assumptions"],
    ),
    GroundTruthAssertion(
        assertion_id="signal_non_full_height_wall",
        field_type="tasks",
        description="Non-full-height wall signal present",
        expected="Scope notes wall is not full height.",
        required_terms=["non-full-height"],
        search_sections=["description", "tasks", "assumptions"],
    ),
    GroundTruthAssertion(
        assertion_id="task_wall_opening",
        field_type="tasks",
        description="Wall opening/demolition present",
        expected="Scope includes opening an existing wall.",
        required_terms=["opening", "wall"],
        search_sections=["description", "tasks"],
    ),
    GroundTruthAssertion(
        assertion_id="measurement_drainage_100mm",
        field_type="measurements",
        description="100mm drainage/evacuation present",
        expected="Scope preserves 100 mm drainage requirement.",
        required_terms=["100", "drainage"],
        search_sections=["description", "tasks", "materials", "clarifying_questions"],
    ),
    GroundTruthAssertion(
        assertion_id="task_water_heater",
        field_type="tasks",
        description="Water heater install/connect present",
        expected="Scope includes water heater installation or connection.",
        required_terms=["water heater"],
        search_sections=["description", "tasks", "materials", "clarifying_questions"],
    ),
    GroundTruthAssertion(
        assertion_id="material_placo_partition",
        field_type="materials",
        description="Placo/partition material present",
        expected="Materials include placo or partition material.",
        required_terms=["placo"],
        search_sections=["materials", "description", "tasks"],
    ),
    GroundTruthAssertion(
        assertion_id="material_water_heater",
        field_type="materials",
        description="Water heater material present",
        expected="Materials include water heater.",
        required_terms=["water heater"],
        search_sections=["materials", "description", "tasks"],
    ),
    GroundTruthAssertion(
        assertion_id="question_wall_location",
        field_type="clarifying_questions",
        description="Must-have question about wall length/location present",
        expected="Clarify wall length or location.",
        required_terms=["wall", "location"],
        search_sections=["clarifying_questions"],
    ),
    GroundTruthAssertion(
        assertion_id="question_waterproofing",
        field_type="clarifying_questions",
        description="Must-have question about shower fixture/waterproofing present",
        expected="Clarify shower fixtures or waterproofing.",
        required_terms=["waterproofing"],
        search_sections=["clarifying_questions"],
    ),
    GroundTruthAssertion(
        assertion_id="question_water_heater",
        field_type="clarifying_questions",
        description="Must-have question about water heater type/capacity/electrical present",
        expected="Clarify water heater capacity or electrical requirements.",
        required_terms=["water heater", "capacity"],
        search_sections=["clarifying_questions"],
    ),
    GroundTruthAssertion(
        assertion_id="pricing_not_ready",
        field_type="pricing_readiness",
        description="Pricing ready is false",
        expected="pricing_ready is false because blockers remain.",
        required_terms=["pricing_ready false"],
        search_sections=["pricing_readiness"],
    ),
    GroundTruthAssertion(
        assertion_id="no_photo_only_task",
        field_type="tasks",
        description="No photo-only task for exposed stone/ceiling lighting/clutter",
        expected="Photo-only existing context does not become requested work.",
        required_terms=["exposed stone", "ceiling lighting", "clutter"],
        search_sections=["tasks"],
        must_be_absent=True,
    ),
    GroundTruthAssertion(
        assertion_id="unsupported_floor_area_not_claimed",
        field_type="safety",
        description="Floor area is not hallucinated",
        expected="Scope should not claim floor_area_m2 because reliable dimensions are unavailable.",
        required_terms=["floor_area_m2"],
        search_sections=["title", "description", "tasks", "materials", "assumptions"],
        must_be_absent=True,
    ),
    GroundTruthAssertion(
        assertion_id="unsupported_tva_not_claimed",
        field_type="regulatory",
        description="TVA category is not hallucinated",
        expected="Scope should not assign TVA category because job/regulatory context is insufficient.",
        required_terms=["tva"],
        search_sections=["title", "description", "tasks", "materials", "assumptions"],
        must_be_absent=True,
    ),
]


def evaluate_scope(scope: ScopeBrief, scope_path: str) -> EvalReport:
    section_text = _scope_sections(scope)
    assertion_results = [
        _evaluate_assertion(assertion, section_text) for assertion in GROUND_TRUTH_ASSERTIONS
    ]
    metrics = _field_type_metrics(assertion_results)
    passed = sum(1 for result in assertion_results if result.status == "pass")
    failed = sum(1 for result in assertion_results if result.status == "fail")
    partial = sum(1 for result in assertion_results if result.status == "partial")
    achieved = passed + (partial * 0.5)
    total = len(assertion_results)
    return EvalReport(
        scope_path=scope_path,
        total_assertions=total,
        passed=passed,
        failed=failed,
        partial=partial,
        overall_precision=achieved / total if total else 0.0,
        overall_recall=passed / total if total else 0.0,
        field_type_metrics=metrics,
        assertion_results=assertion_results,
        notes=(
            "Precision is assertion-level precision, not corpus-level extraction precision. "
            "Matching is deterministic case-insensitive substring matching."
        ),
    )


def _evaluate_assertion(
    assertion: GroundTruthAssertion,
    section_text: dict[str, str],
) -> AssertionResult:
    actual = "\n".join(section_text.get(section, "") for section in assertion.search_sections)
    actual_lower = actual.lower()
    matched_terms = [term for term in assertion.required_terms if term.lower() in actual_lower]

    if assertion.must_be_absent:
        status: Literal["pass", "fail", "partial"] = "pass" if not matched_terms else "fail"
    elif len(matched_terms) == len(assertion.required_terms):
        status = "pass"
    elif matched_terms:
        status = "partial"
    else:
        status = "fail"

    return AssertionResult(
        assertion_id=assertion.assertion_id,
        field_type=assertion.field_type,
        status=status,
        expected=assertion.expected,
        actual=actual,
        notes=f"Matched terms: {matched_terms}" if matched_terms else None,
    )


def _field_type_metrics(results: list[AssertionResult]) -> list[FieldTypeMetrics]:
    by_type: dict[str, list[AssertionResult]] = defaultdict(list)
    for result in results:
        by_type[result.field_type].append(result)

    metrics: list[FieldTypeMetrics] = []
    for field_type, field_results in sorted(by_type.items()):
        passed = sum(1 for result in field_results if result.status == "pass")
        failed = sum(1 for result in field_results if result.status == "fail")
        partial = sum(1 for result in field_results if result.status == "partial")
        achieved = passed + (partial * 0.5)
        total = len(field_results)
        metrics.append(
            FieldTypeMetrics(
                field_type=field_type,
                total_assertions=total,
                passed=passed,
                failed=failed,
                partial=partial,
                precision=achieved / total if total else 0.0,
                recall=passed / total if total else 0.0,
            )
        )
    return metrics


def _scope_sections(scope: ScopeBrief) -> dict[str, str]:
    pricing_ready = (
        scope.pricing_readiness.pricing_ready
        if scope.pricing_readiness is not None
        else None
    )
    return {
        "title": scope.title.value,
        "description": scope.description.value,
        "site_context": scope.site_context.value or "",
        "tasks": "\n".join(
            f"{task.name.value} {task.point_a.value} {task.point_b.value}" for task in scope.tasks
        ),
        "materials": "\n".join(
            f"{material.name.value} {material.estimated_quantity.value} {material.unit}"
            for material in scope.materials
        ),
        "assumptions": "\n".join(assumption.value for assumption in scope.assumptions),
        "exclusions": "\n".join(exclusion.value for exclusion in scope.exclusions),
        "clarifying_questions": "\n".join(
            f"{question.severity.value} {question.question} {question.reason}"
            for question in scope.clarifying_questions
        ),
        "pricing_readiness": f"pricing_ready {str(pricing_ready).lower()}",
    }
