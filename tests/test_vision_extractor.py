import pytest

from scope_modeler.extractors import (
    ExtractorResult,
    VisionDraftQuestion,
    VisionDraftTask,
    VisionExtractionDraft,
    OpenAIVisionExtractionResponse,
    VisionExtractor,
    VisionObservation,
)
from scope_modeler.extractors.vision import _to_openai_strict_json_schema
from scope_modeler.inputs import load_manifest
from scope_modeler.models import GapSeverity, Modality, TaskCategory


class FakeVisionModelClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.real_api_calls = 0

    def extract_from_image(
        self,
        image_path,
        language_hint: str | None = None,
    ) -> VisionExtractionDraft:
        self.calls.append((str(image_path), language_hint))
        return VisionExtractionDraft(
            image_quality="usable with some ambiguity",
            visible_elements=["unfinished wall surface", "visible floor area"],
            unclear_regions=["far corner partially occluded"],
            observations=[
                VisionObservation(
                    label="existing_wall_surface_visible",
                    value=True,
                    confidence=0.78,
                    notes="Surface is visible but exact substrate is uncertain.",
                )
            ],
            tasks=[
                VisionDraftTask(
                    task_id="photo_task_001",
                    category=TaskCategory.GENERAL,
                    name="Verify visible existing conditions",
                    point_a="Existing site conditions visible in photo.",
                    point_b="Visible constraints confirmed before pricing.",
                    step_number=1,
                    confidence=0.72,
                )
            ],
            clarifying_questions=[
                VisionDraftQuestion(
                    question="Confirm hidden conditions outside the photo frame.",
                    severity=GapSeverity.NICE_TO_HAVE,
                    reason="The image does not show the entire work area.",
                    related_task_ids=["photo_task_001"],
                    rank=1,
                    confidence=0.7,
                )
            ],
            confidence=0.76,
            raw_output={"client": "fake"},
        )


def test_vision_extractor_maps_photo_draft_to_extractor_result():
    manifest = load_manifest("data/input/manifest.json")
    capture = manifest.get_capture("photo_001")
    client = FakeVisionModelClient()

    assert capture is not None
    result = VisionExtractor(client).extract(capture)

    assert isinstance(result, ExtractorResult)
    assert result.modality == Modality.PHOTO
    assert result.capture_id == "photo_001"
    assert {"image_quality", "visible_elements", "unclear_regions"}.issubset(
        {observation.label for observation in result.observations}
    )
    assert all(
        observation.provenance.capture_id == "photo_001"
        for observation in result.observations
    )
    assert result.candidate_tasks
    assert result.raw_output["normalized_draft"]["image_quality"] == "usable with some ambiguity"
    assert len(client.calls) == 1
    assert client.real_api_calls == 0


def test_vision_extractor_rejects_non_photo_capture():
    manifest = load_manifest("data/input/manifest.json")
    capture = manifest.get_capture("text_note_001")

    assert capture is not None
    with pytest.raises(ValueError):
        VisionExtractor(FakeVisionModelClient()).extract(capture)

def test_openai_response_schema_excludes_internal_raw_output():
    raw_schema = OpenAIVisionExtractionResponse.model_json_schema()
    strict_schema = _to_openai_strict_json_schema(raw_schema)

    assert "raw_output" not in strict_schema["properties"]
    assert "raw_output" not in strict_schema["required"]


def test_openai_strict_schema_requires_all_object_properties():
    strict_schema = _to_openai_strict_json_schema(
        OpenAIVisionExtractionResponse.model_json_schema()
    )

    top_level_properties = set(strict_schema["properties"].keys())
    assert set(strict_schema["required"]) == top_level_properties
    assert strict_schema["additionalProperties"] is False

    question_schema = strict_schema["$defs"]["VisionDraftQuestion"]
    question_properties = set(question_schema["properties"].keys())
    assert set(question_schema["required"]) == question_properties
    assert "related_task_ids" in question_schema["required"]
    assert question_schema["additionalProperties"] is False


def test_openai_strict_schema_removes_defaults_titles_descriptions_and_ref_siblings():
    strict_schema = _to_openai_strict_json_schema(
        OpenAIVisionExtractionResponse.model_json_schema()
    )

    assert not _contains_key(strict_schema, "default")
    assert not _contains_key(strict_schema, "title")
    assert not _contains_key(strict_schema, "description")
    assert not _contains_ref_with_siblings(strict_schema)


def test_openai_strict_schema_sets_additional_properties_false_on_all_objects():
    strict_schema = _to_openai_strict_json_schema(
        OpenAIVisionExtractionResponse.model_json_schema()
    )

    assert not _contains_object_with_properties_missing_additional_properties_false(
        strict_schema
    )

def _contains_key(node, key: str) -> bool:
    if isinstance(node, dict):
        return key in node or any(_contains_key(value, key) for value in node.values())
    if isinstance(node, list):
        return any(_contains_key(item, key) for item in node)
    return False


def _contains_ref_with_siblings(node) -> bool:
    if isinstance(node, dict):
        if "$ref" in node and set(node.keys()) != {"$ref"}:
            return True
        return any(_contains_ref_with_siblings(value) for value in node.values())
    if isinstance(node, list):
        return any(_contains_ref_with_siblings(item) for item in node)
    return False

def _contains_object_with_properties_missing_additional_properties_false(node) -> bool:
    if isinstance(node, dict):
        if "properties" in node and node.get("additionalProperties") is not False:
            return True
        return any(
            _contains_object_with_properties_missing_additional_properties_false(value)
            for value in node.values()
        )
    if isinstance(node, list):
        return any(
            _contains_object_with_properties_missing_additional_properties_false(item)
            for item in node
        )
    return False