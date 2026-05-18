import pytest

from scope_modeler.extractors import (
    ExtractorResult,
    VisionDraftQuestion,
    VisionDraftTask,
    VisionExtractionDraft,
    VisionExtractor,
    VisionObservation,
)
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
