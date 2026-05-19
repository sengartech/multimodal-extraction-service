from scope_modeler.extractors import (
    DrawingDimension,
    DrawingGeometrySummary,
    DrawingPoint,
    DrawingPrimitive,
    DrawingSemanticInference,
    ExtractedObservation,
    ExtractorResult,
    OpenAITwoPassDrawingParser,
    TwoPassDrawingParser,
)
from scope_modeler.inputs import load_manifest
from scope_modeler.models import (
    GapSeverity,
    Modality,
    Provenance,
    Task,
    TaskCategory,
    VersionedField,
    ClarifyingQuestion,
)
from scope_modeler.llm.schema import to_openai_strict_json_schema
from scope_modeler.extractors.drawing import OpenAIDrawingGeometryResponse


def drawing_capture():
    manifest = load_manifest("data/input/manifest.json")
    capture = manifest.get_capture("drawing_floor_plan_001")

    assert capture is not None
    return capture


def test_two_pass_drawing_parser_pass_1_returns_geometry_summary():
    parser = TwoPassDrawingParser()
    geometry_summary = parser.pass_1_extract_geometry(drawing_capture())

    assert isinstance(geometry_summary, DrawingGeometrySummary)
    assert geometry_summary.capture_id == "drawing_floor_plan_001"
    assert geometry_summary.primitives
    assert geometry_summary.dimensions


def test_two_pass_drawing_parser_pass_2_returns_semantic_inference():
    parser = TwoPassDrawingParser()
    capture = drawing_capture()
    geometry_summary = parser.pass_1_extract_geometry(capture)
    semantic_inference = parser.pass_2_infer_semantics(capture, geometry_summary)

    assert isinstance(semantic_inference, DrawingSemanticInference)
    assert semantic_inference.observations
    assert semantic_inference.candidate_tasks
    assert semantic_inference.clarifying_questions


def test_two_pass_drawing_parser_extract_returns_drawing_result():
    parser = TwoPassDrawingParser()
    result = parser.extract(drawing_capture())

    assert isinstance(result, ExtractorResult)
    assert result.modality == Modality.DRAWING
    assert result.capture_id == "drawing_floor_plan_001"
    assert "geometry_summary" in result.raw_output
    assert "semantic_inference" in result.raw_output
    assert result.clarifying_questions
    assert all(
        observation.provenance.capture_id == "drawing_floor_plan_001"
        for observation in result.observations
    )


def test_openai_two_pass_drawing_parser_calls_geometry_then_semantics():
    calls: list[str] = []
    geometry_client = FakeDrawingGeometryClient(calls)
    semantic_client = FakeDrawingSemanticClient(calls)

    result = OpenAITwoPassDrawingParser(
        geometry_client=geometry_client,
        semantic_client=semantic_client,
    ).extract(drawing_capture())

    assert calls == ["geometry", "semantic"]
    assert isinstance(result, ExtractorResult)
    assert result.modality == Modality.DRAWING
    assert result.capture_id == "drawing_floor_plan_001"
    assert "geometry_summary" in result.raw_output
    assert "semantic_inference" in result.raw_output
    assert result.clarifying_questions
    assert result.clarifying_questions[0].severity == GapSeverity.MUST_HAVE
    assert all(
        observation.provenance.capture_id == "drawing_floor_plan_001"
        for observation in result.observations
    )
    assert all(
        observation.provenance.modality == Modality.DRAWING
        for observation in result.observations
    )


class FakeDrawingGeometryClient:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def extract_geometry(
        self,
        image_path,
        language_hint: str | None = None,
    ) -> DrawingGeometrySummary:
        self.calls.append("geometry")
        return DrawingGeometrySummary(
            capture_id="drawing_floor_plan_001",
            image_path=image_path,
            primitives=[
                DrawingPrimitive(
                    primitive_id="primitive_wall_001",
                    primitive_type="wall_lines",
                    label="partition wall line",
                    points=[DrawingPoint(x=0.0, y=0.0), DrawingPoint(x=1.0, y=1.0)],
                    confidence=0.62,
                )
            ],
            dimensions=[
                DrawingDimension(
                    label="partition_length",
                    value=None,
                    unit="m",
                    is_explicit=False,
                    confidence=0.2,
                )
            ],
            labels=["vestiaire"],
            confidence=0.58,
        )


def test_openai_drawing_geometry_schema_has_array_items_for_points():
    strict_schema = to_openai_strict_json_schema(
        OpenAIDrawingGeometryResponse.model_json_schema()
    )
    point_array = strict_schema["$defs"]["DrawingPrimitive"]["properties"]["points"]

    assert point_array["type"] == "array"
    assert "items" in point_array


class FakeDrawingSemanticClient:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def infer_semantics(
        self,
        geometry_summary: DrawingGeometrySummary,
    ) -> DrawingSemanticInference:
        self.calls.append("semantic")
        provenance = Provenance(
            modality=Modality.DRAWING,
            capture_id=geometry_summary.capture_id,
            extractor="fake_semantic_client",
            confidence=0.6,
        )
        return DrawingSemanticInference(
            inferred_work_area="Approximate staff changing room plan area",
            observations=[
                ExtractedObservation(
                    label="possible_partition_wall",
                    value=True,
                    confidence=0.6,
                    provenance=provenance,
                )
            ],
            candidate_tasks=[
                Task(
                    task_id="drawing_task_001",
                    category=TaskCategory.WALLS,
                    name=VersionedField[str](
                        value="Verify partition layout",
                        confidence=0.6,
                        provenance=[provenance],
                    ),
                    point_a=VersionedField[str](
                        value="Ambiguous hand-drawn wall layout",
                        confidence=0.6,
                        provenance=[provenance],
                    ),
                    point_b=VersionedField[str](
                        value="Confirmed wall layout",
                        confidence=0.6,
                        provenance=[provenance],
                    ),
                    step_number=1,
                    confidence=0.6,
                    provenance=[provenance],
                )
            ],
            clarifying_questions=[
                ClarifyingQuestion(
                    question="Confirm missing wall dimensions.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="The drawing does not provide enough dimensions for pricing.",
                    related_task_ids=["drawing_task_001"],
                    rank=1,
                )
            ],
            confidence=0.6,
        )
