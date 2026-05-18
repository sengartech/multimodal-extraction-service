from scope_modeler.extractors import (
    AudioScopeExtractor,
    DraftObservation,
    DraftQuestion,
    DraftTask,
    ExtractorResult,
    MockTranscriber,
    TextExtractionDraft,
)
from scope_modeler.inputs import load_manifest
from scope_modeler.models import GapSeverity, Modality, TaskCategory


class FakeTextModelClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.real_api_calls = 0

    def extract_construction_scope(
        self,
        text: str,
        language: str | None,
    ) -> TextExtractionDraft:
        self.calls.append((text, language))
        return TextExtractionDraft(
            observations=[
                DraftObservation(label="requested_work", value="staff shower works", confidence=0.9),
            ],
            tasks=[
                DraftTask(
                    task_id="audio_task_001",
                    category=TaskCategory.PLUMBING,
                    name="Assess audio-described plumbing scope",
                    point_a="Existing site conditions described in voice note.",
                    point_b="Plumbing scope captured for downstream fusion.",
                    step_number=1,
                    confidence=0.82,
                )
            ],
            clarifying_questions=[
                DraftQuestion(
                    question="Confirm dimensions mentioned in the voice note.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="Audio transcript does not provide enough measurement certainty.",
                    related_task_ids=["audio_task_001"],
                    rank=1,
                    confidence=0.8,
                )
            ],
            confidence=0.84,
            raw_output={"client": "fake"},
        )


def test_audio_scope_extractor_transcribes_and_maps_to_extractor_result():
    manifest = load_manifest("data/input/manifest.json")
    capture = manifest.get_capture("audio_mock_001")
    client = FakeTextModelClient()

    assert capture is not None
    result = AudioScopeExtractor(
        transcriber=MockTranscriber(),
        text_model_client=client,
    ).extract(capture)

    assert isinstance(result, ExtractorResult)
    assert result.modality == Modality.AUDIO
    assert result.capture_id == "audio_mock_001"
    assert result.candidate_tasks
    assert result.observations[0].provenance.modality == Modality.AUDIO
    assert result.observations[0].provenance.capture_id == "audio_mock_001"
    assert result.candidate_tasks[0].provenance[0].modality == Modality.AUDIO
    assert "transcription_result" in result.raw_output
    assert "normalized_draft" in result.raw_output
    assert len(client.calls) == 1
    assert client.calls[0][1] == "fr"
    assert client.real_api_calls == 0


def test_mock_transcriber_segments_have_positive_duration():
    manifest = load_manifest("data/input/manifest.json")
    capture = manifest.get_capture("audio_mock_001")

    assert capture is not None
    transcription = MockTranscriber().transcribe(capture)

    assert transcription.segments
    assert all(
        segment.end_seconds > segment.start_seconds
        for segment in transcription.segments
    )
