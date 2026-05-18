"""Extractor contracts and modality-specific adapters."""

from scope_modeler.extractors.base import (
    BaseExtractor,
    ExtractedObservation,
    ExtractorResult,
    ObservationValue,
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

__all__ = [
    "BaseExtractor",
    "DraftMaterial",
    "DraftObservation",
    "DraftQuestion",
    "DraftTask",
    "ExtractedObservation",
    "ExtractorResult",
    "LLMTextExtractor",
    "ObservationValue",
    "TextExtractionDraft",
    "TextModelClient",
]
