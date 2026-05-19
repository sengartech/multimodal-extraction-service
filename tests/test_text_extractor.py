from scope_modeler.extractors import (
    DraftObservation,
    DraftQuestion,
    DraftTask,
    ExtractorResult,
    LLMTextExtractor,
    OpenAITextExtractionResponse,
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
                DraftObservation(label="shower_count", value=2, confidence=0.95),
                DraftObservation(label="partition_wall_height_m", value=2.4, confidence=0.8),
                DraftObservation(label="drainage_diameter_mm", value=50, confidence=0.7),
                DraftObservation(label="water_heater_required", value=True, confidence=0.75),
            ],
            tasks=[
                DraftTask(
                    task_id="task_001",
                    category=TaskCategory.GENERAL,
                    name="Prepare work area",
                    point_a="Existing changing-room area.",
                    point_b="Area protected and ready for works.",
                    step_number=1,
                    confidence=0.85,
                ),
                DraftTask(
                    task_id="task_002",
                    category=TaskCategory.PLUMBING,
                    name="Install supply and drainage",
                    point_a="No confirmed shower plumbing in target location.",
                    point_b="Water supply and drainage ready for fixtures.",
                    step_number=2,
                    confidence=0.82,
                ),
                DraftTask(
                    task_id="task_003",
                    category=TaskCategory.WALLS,
                    name="Build partitions",
                    point_a="Open staff area.",
                    point_b="Partitions define shower spaces.",
                    step_number=3,
                    confidence=0.78,
                ),
                DraftTask(
                    task_id="task_004",
                    category=TaskCategory.WATERPROOFING,
                    name="Waterproof wet zones",
                    point_a="Surfaces not ready for wet use.",
                    point_b="Wet zones waterproofed for shower use.",
                    step_number=4,
                    confidence=0.8,
                ),
            ],
            clarifying_questions=[
                DraftQuestion(
                    question="Confirm available hot-water capacity and connection point.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="Hot-water supply affects sizing and pricing.",
                    related_task_ids=["task_002"],
                    rank=1,
                    confidence=0.9,
                )
            ],
            confidence=0.84,
            raw_output={"client": "fake"},
        )


def test_llm_text_extractor_maps_fixture_text_to_extractor_result():
    manifest = load_manifest("data/input/manifest.json")
    capture = manifest.get_capture("text_note_001")
    client = FakeTextModelClient()

    assert capture is not None
    result = LLMTextExtractor(client).extract(capture)

    assert isinstance(result, ExtractorResult)
    assert client.calls and client.calls[0][1] == "fr"
    assert result.capture_id == "text_note_001"
    assert result.modality == Modality.TEXT

    observation_labels = {observation.label for observation in result.observations}
    assert {
        "shower_count",
        "partition_wall_height_m",
        "drainage_diameter_mm",
        "water_heater_required",
    }.issubset(observation_labels)
    assert len(result.candidate_tasks) >= 4
    assert any(
        question.severity == GapSeverity.MUST_HAVE for question in result.clarifying_questions
    )
    assert all(
        observation.provenance.capture_id == "text_note_001"
        for observation in result.observations
    )
    assert result.candidate_tasks[0].name.provenance[0].capture_id == "text_note_001"
    assert len(client.calls) == 1
    assert client.real_api_calls == 0


def test_openai_text_response_converts_to_text_extraction_draft():
    response = OpenAITextExtractionResponse(
        observations=[
            DraftObservation(label="requested_work", value="Créer deux douches", confidence=0.9)
        ],
        tasks=[],
        materials=[],
        assumptions=[],
        clarifying_questions=[],
        confidence=0.88,
    )

    draft = TextExtractionDraft(
        **response.model_dump(mode="python"),
        raw_output={"provider": "openai", "model": "gpt-5.4"},
    )

    assert draft.observations[0].label == "requested_work"
    assert draft.raw_output["provider"] == "openai"
