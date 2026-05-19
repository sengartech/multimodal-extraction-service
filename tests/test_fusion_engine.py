from scope_modeler.extractors import ExtractedObservation, ExtractorResult
from scope_modeler.fusion import (
    EvidenceBundle,
    FusionDraft,
    FusionDraftMaterial,
    FusionDraftQuestion,
    FusionDraftTask,
    FusionEngine,
    OpenAIFusionResponse,
)
from scope_modeler.fusion.fusion_engine import _to_openai_strict_json_schema
from scope_modeler.models import (
    CaptureType,
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


class FakeFusionModelClient:
    def __init__(self) -> None:
        self.calls: list[EvidenceBundle] = []
        self.real_api_calls = 0

    def synthesize_scope(self, evidence_bundle: EvidenceBundle) -> FusionDraft:
        self.calls.append(evidence_bundle)
        return FusionDraft(
            title="Installation de 2 douches vestiaires",
            description=(
                "Créer deux douches pour vestiaires du personnel avec cloison placo, "
                "ouverture murale, évacuation, chauffe-eau et raccordements."
            ),
            site_context=(
                "Photos: espace existant fini avec plafond bas et contraintes d'accès/encombrement."
            ),
            tasks=[
                FusionDraftTask(
                    task_id="task_shower_001",
                    category=TaskCategory.PLUMBING,
                    name="Installer 2 douches vestiaires",
                    point_a="Espace vestiaire existant sans douches confirmées.",
                    point_b="Deux douches fonctionnelles installées.",
                    step_number=1,
                    confidence=0.84,
                    supporting_capture_ids=["text_note_001", "audio_mock_001"],
                ),
                FusionDraftTask(
                    task_id="task_wall_001",
                    category=TaskCategory.WALLS,
                    name="Monter une cloison placo non pleine hauteur de 2 m",
                    point_a="Zone ouverte sans séparation validée.",
                    point_b="Cloison placo de séparation posée selon implantation confirmée.",
                    step_number=2,
                    confidence=0.78,
                    supporting_capture_ids=["text_note_001", "drawing_floor_plan_001"],
                ),
                FusionDraftTask(
                    task_id="task_opening_001",
                    category=TaskCategory.MASONRY,
                    name="Créer une ouverture dans le mur",
                    point_a="Mur existant ou séparation à ouvrir selon plan.",
                    point_b="Ouverture réalisée et reprise proprement.",
                    step_number=3,
                    confidence=0.75,
                    supporting_capture_ids=["text_note_001", "drawing_floor_plan_001"],
                ),
                FusionDraftTask(
                    task_id="task_drain_001",
                    category=TaskCategory.PLUMBING,
                    name="Prévoir une évacuation Ø100",
                    point_a="Accès évacuation non confirmé.",
                    point_b="Évacuation dimensionnée et raccordée si faisable.",
                    step_number=4,
                    confidence=0.74,
                    supporting_capture_ids=["text_note_001"],
                ),
                FusionDraftTask(
                    task_id="task_heater_001",
                    category=TaskCategory.PLUMBING,
                    name="Installer ou raccorder un chauffe-eau",
                    point_a="Capacité eau chaude non confirmée.",
                    point_b="Production eau chaude adaptée aux douches.",
                    step_number=5,
                    confidence=0.72,
                    supporting_capture_ids=["text_note_001", "photo_001"],
                ),
            ],
            materials=[
                FusionDraftMaterial(
                    material_id="mat_placo_001",
                    name="Plaques de plâtre hydrofuges",
                    estimated_quantity=1.0,
                    unit="lot",
                    related_task_ids=["task_wall_001"],
                    confidence=0.55,
                    supporting_capture_ids=["text_note_001", "drawing_floor_plan_001"],
                )
            ],
            assumptions=["Quantités à confirmer après métrés et accès réseaux."],
            exclusions=["Travaux structurels lourds non confirmés."],
            clarifying_questions=[
                FusionDraftQuestion(
                    question="Confirmer longueur et implantation exacte de la cloison.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="Le plan ne donne pas de dimensions fiables.",
                    related_task_ids=["task_wall_001"],
                    rank=1,
                ),
                FusionDraftQuestion(
                    question="Confirmer accès évacuation, conformité et pente disponible.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="Le raccordement évacuation conditionne le prix.",
                    related_task_ids=["task_drain_001"],
                    rank=2,
                ),
                FusionDraftQuestion(
                    question="Confirmer capacité chauffe-eau et besoins électriques.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="La production d'eau chaude et l'alimentation électrique sont incertaines.",
                    related_task_ids=["task_heater_001"],
                    rank=3,
                ),
                FusionDraftQuestion(
                    question="Confirmer étanchéité, pente de sol et finitions attendues.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="Les finitions de zone humide ne sont pas suffisamment spécifiées.",
                    related_task_ids=["task_shower_001"],
                    rank=4,
                ),
            ],
            unresolved_critical_conflicts=[],
            confidence=0.80,
        )


def test_fusion_engine_returns_scope_brief_from_fake_model_client():
    client = FakeFusionModelClient()
    scope = FusionEngine(client).fuse(
        job_id="wine_bar_staff_showers_001",
        source_captures=source_captures(),
        extractor_results=fake_extractor_results(),
    )

    assert isinstance(scope, ScopeBrief)
    assert scope.title.value
    task_names = " ".join(task.name.value.lower() for task in scope.tasks)
    assert "douches" in task_names
    assert "placo" in task_names
    assert "évacuation" in task_names
    assert "chauffe-eau" in task_names
    assert "low ceiling" not in task_names
    assert "clutter" not in task_names
    assert scope.pricing_readiness is not None
    assert scope.pricing_readiness.pricing_ready is False
    assert any(
        question.severity == GapSeverity.MUST_HAVE
        for question in scope.clarifying_questions
    )
    assert scope.title.provenance
    assert all(task.provenance for task in scope.tasks)
    assert scope.materials[0].name.provenance
    assert scope.materials[0].estimated_quantity.provenance
    assert client.calls
    assert client.calls[0].observations
    assert client.real_api_calls == 0


def test_openai_fusion_response_strict_schema_is_sanitized():
    strict_schema = _to_openai_strict_json_schema(
        OpenAIFusionResponse.model_json_schema()
    )

    top_level_properties = set(strict_schema["properties"].keys())
    assert set(strict_schema["required"]) == top_level_properties
    assert not _contains_schema_keyword(strict_schema, "default")
    assert not _contains_schema_keyword(strict_schema, "title")
    assert not _contains_schema_keyword(strict_schema, "description")
    assert not _contains_ref_with_siblings(strict_schema)
    assert _objects_with_properties_have_no_extra_properties(strict_schema)


def test_openai_fusion_response_converts_to_fusion_draft():
    response = OpenAIFusionResponse(
        title="Installation de 2 douches vestiaires",
        description="Créer deux douches vestiaires.",
        site_context=None,
        tasks=[],
        materials=[],
        assumptions=[],
        exclusions=[],
        clarifying_questions=[],
        unresolved_critical_conflicts=[],
        confidence=0.8,
    )

    draft = FusionDraft.model_validate(response.model_dump(mode="python"))

    assert draft.title == response.title
    assert draft.site_context is None
    assert draft.tasks == []


def source_captures() -> list[SourceCapture]:
    return [
        SourceCapture(
            capture_id="text_note_001",
            capture_type=CaptureType.CONTRACTOR_NOTE,
            modality=Modality.TEXT,
            path="data/input/customer_text_fr.txt",
            language="fr",
        ),
        SourceCapture(
            capture_id="audio_mock_001",
            capture_type=CaptureType.AUDIO_RECORDING,
            modality=Modality.AUDIO,
            path="data/input/audios/mock_voice_note_fr.txt",
            language="fr",
        ),
        SourceCapture(
            capture_id="drawing_floor_plan_001",
            capture_type=CaptureType.FLOOR_PLAN,
            modality=Modality.DRAWING,
            path="data/input/drawings/floor_plan.png",
        ),
        SourceCapture(
            capture_id="photo_001",
            capture_type=CaptureType.SITE_PHOTO,
            modality=Modality.PHOTO,
            path="data/input/photos/photo_01.png",
        ),
    ]


def fake_extractor_results() -> list[ExtractorResult]:
    return [
        ExtractorResult(
            capture_id="text_note_001",
            extractor_name="llm_text_extractor_v1",
            modality=Modality.TEXT,
            observations=[
                observation("text_note_001", Modality.TEXT, "requested_showers", 2, 0.92),
                observation("text_note_001", Modality.TEXT, "drainage_diameter_mm", 100, 0.82),
            ],
            candidate_tasks=[
                task(
                    "text_task_shower",
                    "Créer deux douches vestiaires",
                    TaskCategory.PLUMBING,
                    "text_note_001",
                    Modality.TEXT,
                )
            ],
            confidence=0.86,
            raw_output={},
        ),
        ExtractorResult(
            capture_id="photo_001",
            extractor_name="vision_extractor_v1",
            modality=Modality.PHOTO,
            observations=[
                observation("photo_001", Modality.PHOTO, "low_ceiling", True, 0.74),
                observation("photo_001", Modality.PHOTO, "clutter_access_constraint", True, 0.70),
            ],
            confidence=0.74,
            raw_output={},
        ),
        ExtractorResult(
            capture_id="drawing_floor_plan_001",
            extractor_name="two_pass_drawing_parser_v1",
            modality=Modality.DRAWING,
            observations=[
                observation(
                    "drawing_floor_plan_001",
                    Modality.DRAWING,
                    "dimension_confidence",
                    0.45,
                    0.45,
                )
            ],
            clarifying_questions=[],
            confidence=0.45,
            raw_output={},
        ),
    ]


def observation(
    capture_id: str,
    modality: Modality,
    label: str,
    value,
    confidence: float,
) -> ExtractedObservation:
    return ExtractedObservation(
        label=label,
        value=value,
        confidence=confidence,
        provenance=Provenance(
            modality=modality,
            capture_id=capture_id,
            extractor="test_extractor",
            confidence=confidence,
        ),
    )


def task(
    task_id: str,
    name: str,
    category: TaskCategory,
    capture_id: str,
    modality: Modality,
) -> Task:
    prov = Provenance(
        modality=modality,
        capture_id=capture_id,
        extractor="test_extractor",
        confidence=0.82,
    )
    return Task(
        task_id=task_id,
        category=category,
        name=VersionedField[str](value=name, confidence=0.82, provenance=[prov]),
        point_a=VersionedField[str](value="Existing state", confidence=0.82, provenance=[prov]),
        point_b=VersionedField[str](value="Final state", confidence=0.82, provenance=[prov]),
        step_number=1,
        confidence=0.82,
        provenance=[prov],
    )


def _contains_schema_keyword(node, key: str) -> bool:
    if isinstance(node, dict):
        for node_key, value in node.items():
            if node_key == key:
                return True
            if node_key == "properties" and isinstance(value, dict):
                if any(_contains_schema_keyword(schema, key) for schema in value.values()):
                    return True
                continue
            if _contains_schema_keyword(value, key):
                return True
    if isinstance(node, list):
        return any(_contains_schema_keyword(item, key) for item in node)
    return False


def _contains_ref_with_siblings(node) -> bool:
    if isinstance(node, dict):
        if "$ref" in node and set(node.keys()) != {"$ref"}:
            return True
        return any(_contains_ref_with_siblings(value) for value in node.values())
    if isinstance(node, list):
        return any(_contains_ref_with_siblings(item) for item in node)
    return False


def _objects_with_properties_have_no_extra_properties(node) -> bool:
    if isinstance(node, dict):
        if "properties" in node and node.get("additionalProperties") is not False:
            return False
        return all(
            _objects_with_properties_have_no_extra_properties(value)
            for value in node.values()
        )
    if isinstance(node, list):
        return all(_objects_with_properties_have_no_extra_properties(item) for item in node)
    return True
