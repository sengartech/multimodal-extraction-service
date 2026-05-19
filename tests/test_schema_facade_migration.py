from scope_modeler.models import (
    AccessRequirement,
    CaptureType,
    Modality,
    Provenance,
    RegulatoryRequirement,
    ScopeBrief,
    SourceCapture,
    Task,
    TaskCategory,
    VersionedField,
    WorkArea,
)


def test_existing_minimal_scope_validates_without_new_fields():
    scope = minimal_scope()

    assert scope.work_areas == []
    assert scope.access_requirements == []
    assert scope.regulatory_requirements == []
    assert scope.pricing_readiness is not None
    assert scope.pricing_readiness.pricing_ready is True


def test_facade_scope_represents_work_area_access_and_regulatory_requirements():
    scope = ScopeBrief(
        job_id="haussmann_facade_001",
        title=field("Haussmannian facade renovation"),
        description=field("Ravalement de facade on the entire street-facing wall."),
        tasks=[
            task("task_facade_cleaning", 1, 0.86).model_copy(
                update={"category": TaskCategory.FACADE}
            )
        ],
        work_areas=[
            WorkArea(
                area_id="facade_street_001",
                label="Street-facing facade",
                area_type="facade",
                location="Exterior street-facing wall",
                surface_m2=None,
                notes="No room model is required for facade work.",
                confidence=0.88,
                provenance=[provenance()],
            )
        ],
        access_requirements=[
            AccessRequirement(
                requirement_id="access_scaffold_001",
                requirement_type="scaffolding",
                description="Scaffolding required for street-facing facade works.",
                required=True,
                confidence=0.9,
                provenance=[provenance()],
            )
        ],
        regulatory_requirements=[
            RegulatoryRequirement(
                requirement_id="reg_dp_001",
                regime="declaration_prealable",
                description="Declaration prealable may be required for facade renovation.",
                status="possibly_required",
                blocking=True,
                confidence=0.8,
                provenance=[provenance()],
            ),
            RegulatoryRequirement(
                requirement_id="reg_abf_001",
                regime="batiments_de_france",
                description="Batiments de France review may apply in protected zones.",
                status="possibly_required",
                blocking=True,
                confidence=0.7,
                provenance=[provenance()],
            ),
            RegulatoryRequirement(
                requirement_id="reg_copro_001",
                regime="copropriete_authorization",
                description="Copropriete authorization is required or likely required.",
                status="required",
                blocking=True,
                confidence=0.85,
                provenance=[provenance()],
            ),
        ],
    )

    assert scope.work_areas[0].area_type == "facade"
    assert scope.access_requirements[0].requirement_type == "scaffolding"
    assert {requirement.regime for requirement in scope.regulatory_requirements} == {
        "declaration_prealable",
        "batiments_de_france",
        "copropriete_authorization",
    }
    assert scope.pricing_readiness is not None
    assert scope.pricing_readiness.pricing_ready is False
    assert "blocking_regulatory_requirements" in scope.pricing_readiness.blocking_reasons


def provenance() -> Provenance:
    return Provenance(
        modality=Modality.TEXT,
        capture_id="facade_note_001",
        extractor="test",
        confidence=0.9,
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


def field(value: str, confidence: float = 0.9) -> VersionedField[str]:
    return VersionedField[str](
        value=value,
        confidence=confidence,
        provenance=[provenance()],
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
        provenance=[provenance()],
    )
