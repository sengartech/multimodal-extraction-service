import pytest
from pydantic import ValidationError

from scope_modeler.fusion import FusionEngine, FusionDraft, FusionModelClient
from scope_modeler.extractors.base import ExtractedObservation, ExtractorResult
from scope_modeler.models import (
    CaptureType,
    GapSeverity,
    Modality,
    Provenance,
    ScopeBrief,
    SourceCapture,
)


class FakeConflictAwareFusionClient:
    def synthesize_scope(self, evidence_bundle):
        evidence_text = evidence_bundle.model_dump_json().lower()

        # Verify the fusion client received both modalities and the conflicting signal.
        assert "photo_001" in evidence_text
        assert "drawing_floor_plan_001" in evidence_text
        assert "opening_count" in evidence_text

        return FusionDraft(
            title="Layout conflict requires confirmation",
            description="Photo and drawing evidence disagree, so scope is not pricing-ready.",
            site_context="Photo suggests one opening; drawing suggests two openings.",
            tasks=[],
            materials=[],
            assumptions=[
                "Visual and drawing evidence disagree about the opening/layout condition."
            ],
            exclusions=[],
            clarifying_questions=[
                {
                    "question": "Confirm whether the room has one or two openings.",
                    "severity": GapSeverity.MUST_HAVE,
                    "reason": "Photo and drawing evidence disagree.",
                    "related_task_ids": [],
                    "rank": 1,
                }
            ],
            unresolved_critical_conflicts=[
                "Photo and drawing disagree about opening count."
            ],
            confidence=0.55,
        )


def test_cross_modal_disagreement_blocks_pricing():
    source_captures = [
        SourceCapture(
            capture_id="photo_001",
            capture_type=CaptureType.SITE_PHOTO,
            modality=Modality.PHOTO,
        ),
        SourceCapture(
            capture_id="drawing_floor_plan_001",
            capture_type=CaptureType.FLOOR_PLAN,
            modality=Modality.DRAWING,
        ),
    ]

    extractor_results = [
        ExtractorResult(
            capture_id="photo_001",
            extractor_name="test_photo",
            modality=Modality.PHOTO,
            observations=[
                ExtractedObservation(
                    label="opening_count",
                    value=1,
                    confidence=0.7,
                    provenance=Provenance(
                        modality=Modality.PHOTO,
                        capture_id="photo_001",
                        extractor="test_photo",
                        confidence=0.7,
                    ),
                    notes="Photo suggests one visible opening.",
                )
            ],
            confidence=0.7,
        ),
        ExtractorResult(
            capture_id="drawing_floor_plan_001",
            extractor_name="test_drawing",
            modality=Modality.DRAWING,
            observations=[
                ExtractedObservation(
                    label="opening_count",
                    value=2,
                    confidence=0.6,
                    provenance=Provenance(
                        modality=Modality.DRAWING,
                        capture_id="drawing_floor_plan_001",
                        extractor="test_drawing",
                        confidence=0.6,
                    ),
                    notes="Drawing suggests two possible openings.",
                )
            ],
            confidence=0.6,
        ),
    ]

    scope = FusionEngine(FakeConflictAwareFusionClient()).fuse(
        job_id="conflict_case",
        source_captures=source_captures,
        extractor_results=extractor_results,
    )

    assert scope.pricing_readiness.pricing_ready is False
    assert scope.unresolved_critical_conflicts
    assert any(
        question.severity == GapSeverity.MUST_HAVE
        for question in scope.clarifying_questions
    )


def test_scope_brief_rejects_incomplete_required_input():
    with pytest.raises(ValidationError):
        ScopeBrief.model_validate(
            {
                "job_id": "incomplete",
                # source_captures, title, and description are missing
            }
        )
