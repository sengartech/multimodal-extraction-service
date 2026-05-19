"""Cross-modal fusion, confidence, provenance, and readiness logic."""

from scope_modeler.fusion.fusion_engine import (
    EvidenceBundle,
    EvidenceItem,
    FusionDraft,
    FusionDraftMaterial,
    FusionDraftQuestion,
    FusionDraftTask,
    FusionEngine,
    FusionModelClient,
    OpenAIFusionModelClient,
    OpenAIFusionResponse,
    build_evidence_bundle,
)

__all__ = [
    "EvidenceBundle",
    "EvidenceItem",
    "FusionDraft",
    "FusionDraftMaterial",
    "FusionDraftQuestion",
    "FusionDraftTask",
    "FusionEngine",
    "FusionModelClient",
    "OpenAIFusionModelClient",
    "OpenAIFusionResponse",
    "build_evidence_bundle",
]
