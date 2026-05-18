"""Extractor contracts and modality-specific adapters."""

from scope_modeler.extractors.base import (
    BaseExtractor,
    ExtractedObservation,
    ExtractorResult,
    ObservationValue,
)
from scope_modeler.extractors.audio import (
    AudioScopeExtractor,
    MockTranscriber,
    Transcriber,
    TranscriptionResult,
    TranscriptionSegment,
)
from scope_modeler.extractors.drawing import (
    DrawingDimension,
    DrawingGeometrySummary,
    DrawingPrimitive,
    DrawingSemanticInference,
    TwoPassDrawingParser,
)
from scope_modeler.extractors.text import (
    DraftMaterial,
    DraftObservation,
    DraftQuestion,
    DraftTask,
    LLMTextExtractor,
    TextExtractionDraft,
    TextModelClient,
)
from scope_modeler.extractors.vision import (
    OpenAIVisionModelClient,
    VisionDraftMaterial,
    VisionDraftQuestion,
    VisionDraftTask,
    VisionExtractionDraft,
    VisionExtractor,
    VisionModelClient,
    VisionObservation,
)

__all__ = [
    "BaseExtractor",
    "AudioScopeExtractor",
    "DrawingDimension",
    "DrawingGeometrySummary",
    "DrawingPrimitive",
    "DrawingSemanticInference",
    "DraftMaterial",
    "DraftObservation",
    "DraftQuestion",
    "DraftTask",
    "ExtractedObservation",
    "ExtractorResult",
    "LLMTextExtractor",
    "MockTranscriber",
    "ObservationValue",
    "OpenAIVisionModelClient",
    "TextExtractionDraft",
    "TextModelClient",
    "Transcriber",
    "TranscriptionResult",
    "TranscriptionSegment",
    "TwoPassDrawingParser",
    "VisionDraftMaterial",
    "VisionDraftQuestion",
    "VisionDraftTask",
    "VisionExtractionDraft",
    "VisionExtractor",
    "VisionModelClient",
    "VisionObservation",
]
