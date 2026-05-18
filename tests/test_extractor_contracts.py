from pathlib import Path

import pytest
from pydantic import ValidationError

from scope_modeler.extractors import BaseExtractor, ExtractedObservation, ExtractorResult
from scope_modeler.inputs import InputCapture
from scope_modeler.models import CaptureType, Modality, Provenance


def provenance(confidence: float = 0.9) -> Provenance:
    return Provenance(
        modality=Modality.TEXT,
        capture_id="text_note_001",
        extractor="fake_text_extractor",
        confidence=confidence,
    )


def input_capture() -> InputCapture:
    return InputCapture(
        capture_id="text_note_001",
        capture_type=CaptureType.CONTRACTOR_NOTE,
        modality=Modality.TEXT,
        path=Path("data/input/customer_text_fr.txt"),
        language="fr",
    )


class FakeTextExtractor:
    extractor_name = "fake_text_extractor"
    supported_modalities = (Modality.TEXT,)

    def extract(self, capture: InputCapture) -> ExtractorResult:
        return ExtractorResult(
            capture_id=capture.capture_id,
            extractor_name=self.extractor_name,
            modality=capture.modality,
            observations=[
                ExtractedObservation(
                    label="requested_work",
                    value="Create two staff changing-room showers.",
                    confidence=0.85,
                    provenance=provenance(0.85),
                )
            ],
            confidence=0.85,
            raw_output={"source": "fake"},
        )


def test_extractor_result_validates_confidence_range():
    with pytest.raises(ValidationError):
        ExtractorResult(
            capture_id="text_note_001",
            extractor_name="fake_text_extractor",
            modality=Modality.TEXT,
            confidence=1.1,
            raw_output={},
        )


def test_extracted_observation_validates_confidence_range():
    with pytest.raises(ValidationError):
        ExtractedObservation(
            label="requested_work",
            value="Create two staff changing-room showers.",
            confidence=-0.1,
            provenance=provenance(),
        )


def test_simple_fake_extractor_returns_extractor_result():
    result = FakeTextExtractor().extract(input_capture())

    assert isinstance(result, ExtractorResult)
    assert result.capture_id == "text_note_001"
    assert result.observations[0].label == "requested_work"
    assert result.confidence == 0.85


def test_fake_extractor_can_be_used_through_base_extractor_type():
    extractor: BaseExtractor = FakeTextExtractor()

    assert isinstance(extractor, BaseExtractor)
    assert extractor.supported_modalities == (Modality.TEXT,)
    assert extractor.extractor_name == "fake_text_extractor"
    assert extractor.extract(input_capture()).modality == Modality.TEXT
