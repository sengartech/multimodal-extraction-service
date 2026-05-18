"""Audio extractor scaffold with a mock transcriber."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.extractors.base import ExtractorResult
from scope_modeler.extractors.text import (
    TextModelClient,
    map_text_draft_to_extractor_result,
)
from scope_modeler.inputs import InputCapture
from scope_modeler.models import Modality


class TranscriptionSegment(BaseModel):
    """A segment of transcribed audio."""

    model_config = ConfigDict(extra="forbid")

    text: str
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)


class TranscriptionResult(BaseModel):
    """Full transcription result returned by a transcriber implementation."""

    model_config = ConfigDict(extra="forbid")

    text: str
    language: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    segments: list[TranscriptionSegment] = Field(default_factory=list)


class Transcriber(Protocol):
    """Transcription boundary ready for a faster-whisper implementation later."""

    def transcribe(self, capture: InputCapture) -> TranscriptionResult:
        """Transcribe an audio capture into text and timed segments."""


class MockTranscriber:
    """Mock transcriber that reads a UTF-8 transcript fixture from capture.path."""

    default_confidence = 0.90

    def transcribe(self, capture: InputCapture) -> TranscriptionResult:
        text = Path(capture.path).read_text(encoding="utf-8")
        duration_seconds = max(len(text.split()) / 2.5, 1.0)
        return TranscriptionResult(
            text=text,
            language=capture.language,
            confidence=self.default_confidence,
            segments=[
                TranscriptionSegment(
                    text=text,
                    start_seconds=0.0,
                    end_seconds=duration_seconds,
                    confidence=self.default_confidence,
                )
            ],
        )


class AudioScopeExtractor:
    """Audio scaffold: transcribe, ask text model, map draft to extractor result."""

    extractor_name = "audio_scope_extractor_v1"
    supported_modalities = (Modality.AUDIO,)

    def __init__(
        self,
        transcriber: Transcriber,
        text_model_client: TextModelClient,
    ) -> None:
        self.transcriber = transcriber
        self.text_model_client = text_model_client

    def extract(self, capture: InputCapture) -> ExtractorResult:
        if capture.modality != Modality.AUDIO:
            raise ValueError(
                f"{self.extractor_name} only supports audio captures, got {capture.modality!s}"
            )

        transcription = self.transcriber.transcribe(capture)
        draft = self.text_model_client.extract_construction_scope(
            transcription.text,
            transcription.language,
        )
        return map_text_draft_to_extractor_result(
            capture=capture,
            draft=draft,
            extractor_name=self.extractor_name,
            modality=Modality.AUDIO,
            raw_output={
                "transcription_result": transcription.model_dump(mode="json"),
                "normalized_draft": draft.model_dump(mode="json"),
            },
        )
