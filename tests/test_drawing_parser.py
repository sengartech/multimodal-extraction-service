from scope_modeler.extractors import (
    DrawingGeometrySummary,
    DrawingSemanticInference,
    ExtractorResult,
    TwoPassDrawingParser,
)
from scope_modeler.inputs import load_manifest
from scope_modeler.models import Modality


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

