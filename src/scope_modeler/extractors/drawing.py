"""Deterministic two-pass drawing parser scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.extractors.base import ExtractedObservation, ExtractorResult
from scope_modeler.inputs import InputCapture
from scope_modeler.models import (
    ClarifyingQuestion,
    GapSeverity,
    Modality,
    Provenance,
    Task,
    TaskCategory,
    VersionedField,
)


class DrawingPrimitive(BaseModel):
    """Low-level geometry primitive identified in a drawing."""

    model_config = ConfigDict(extra="forbid")

    primitive_id: str
    primitive_type: Literal[
        "room_outline",
        "wall_lines",
        "opening_marker",
        "annotation",
        "fixture_symbol",
        "dimension_marker",
        "unknown",
    ]
    label: str | None = None
    points: list[tuple[float, float]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class DrawingDimension(BaseModel):
    """Dimension annotation extracted or marked as unknown from a drawing."""

    model_config = ConfigDict(extra="forbid")

    label: str
    value: float | None = None
    unit: str | None = None
    is_explicit: bool
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class DrawingGeometrySummary(BaseModel):
    """First-pass output: geometry, labels, and dimensions only."""

    model_config = ConfigDict(extra="forbid")

    capture_id: str
    image_path: Path
    primitives: list[DrawingPrimitive] = Field(default_factory=list)
    dimensions: list[DrawingDimension] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class DrawingSemanticInference(BaseModel):
    """Second-pass output: inferred construction semantics from geometry."""

    model_config = ConfigDict(extra="forbid")

    inferred_work_area: str | None = None
    observations: list[ExtractedObservation] = Field(default_factory=list)
    candidate_tasks: list[Task] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class TwoPassDrawingParser:
    """Explicit two-pass parser for hand-drawn renovation floor plans."""

    extractor_name = "two_pass_drawing_parser_v1"
    supported_modalities = (Modality.DRAWING,)

    def extract(self, capture: InputCapture) -> ExtractorResult:
        if capture.modality != Modality.DRAWING:
            raise ValueError(
                f"{self.extractor_name} only supports drawing captures, got {capture.modality!s}"
            )
        if not Path(capture.path).exists():
            raise FileNotFoundError(capture.path)

        geometry_summary = self.pass_1_extract_geometry(capture)
        semantic_inference = self.pass_2_infer_semantics(capture, geometry_summary)
        return ExtractorResult(
            capture_id=capture.capture_id,
            extractor_name=self.extractor_name,
            modality=Modality.DRAWING,
            observations=semantic_inference.observations,
            candidate_tasks=semantic_inference.candidate_tasks,
            clarifying_questions=semantic_inference.clarifying_questions,
            confidence=semantic_inference.confidence,
            raw_output={
                "geometry_summary": geometry_summary.model_dump(mode="json"),
                "semantic_inference": semantic_inference.model_dump(mode="json"),
            },
        )

    def pass_1_extract_geometry(self, capture: InputCapture) -> DrawingGeometrySummary:
        image_path = Path(capture.path)
        if not image_path.exists():
            raise FileNotFoundError(image_path)

        return DrawingGeometrySummary(
            capture_id=capture.capture_id,
            image_path=image_path,
            primitives=[
                DrawingPrimitive(
                    primitive_id="primitive_room_outline_001",
                    primitive_type="room_outline",
                    label="main drawn room boundary",
                    confidence=0.55,
                    notes="Deterministic fixture parser marks the dominant outline; exact scale is unknown.",
                ),
                DrawingPrimitive(
                    primitive_id="primitive_wall_lines_001",
                    primitive_type="wall_lines",
                    label="internal partition or wall strokes",
                    confidence=0.45,
                    notes="Hand-drawn strokes suggest walls or partitions but require confirmation.",
                ),
                DrawingPrimitive(
                    primitive_id="primitive_opening_marker_001",
                    primitive_type="opening_marker",
                    label="possible door/opening marker",
                    confidence=0.35,
                    notes="Opening marker is approximate and not enough for pricing by itself.",
                ),
                DrawingPrimitive(
                    primitive_id="primitive_annotation_001",
                    primitive_type="annotation",
                    label="handwritten labels or arrows",
                    confidence=0.40,
                    notes="Labels are not OCR-parsed in this scaffold.",
                ),
            ],
            dimensions=[
                DrawingDimension(
                    label="overall_room_width",
                    is_explicit=False,
                    confidence=0.15,
                    notes="No reliable OCR/scale extraction implemented yet.",
                ),
                DrawingDimension(
                    label="overall_room_length",
                    is_explicit=False,
                    confidence=0.15,
                    notes="No reliable OCR/scale extraction implemented yet.",
                ),
                DrawingDimension(
                    label="opening_width",
                    is_explicit=False,
                    confidence=0.10,
                    notes="Opening location may be visible, but width is ambiguous.",
                ),
            ],
            labels=[
                "floor plan",
                "possible work area",
                "possible wall/opening annotations",
            ],
            confidence=0.45,
        )

    def pass_2_infer_semantics(
        self,
        capture: InputCapture,
        geometry_summary: DrawingGeometrySummary,
    ) -> DrawingSemanticInference:
        provenance = self._provenance(capture, confidence=0.45)
        inferred_work_area = "Approximate room or work zone shown in the floor plan"
        return DrawingSemanticInference(
            inferred_work_area=inferred_work_area,
            observations=[
                ExtractedObservation(
                    label="inferred_work_area",
                    value=inferred_work_area,
                    confidence=0.45,
                    provenance=provenance,
                    notes="Derived from the first-pass room outline.",
                ),
                ExtractedObservation(
                    label="possible_wall_or_partition_lines",
                    value=True,
                    confidence=0.40,
                    provenance=self._provenance(capture, confidence=0.40),
                    notes="Wall-like strokes are present but not dimensioned.",
                ),
                ExtractedObservation(
                    label="possible_opening",
                    value=True,
                    confidence=0.35,
                    provenance=self._provenance(capture, confidence=0.35),
                    notes="Opening marker requires confirmation before pricing.",
                ),
                ExtractedObservation(
                    label="dimension_confidence",
                    value=geometry_summary.confidence,
                    confidence=geometry_summary.confidence,
                    provenance=self._provenance(capture, confidence=geometry_summary.confidence),
                    notes="Geometry pass is conservative because scale and dimensions are ambiguous.",
                ),
            ],
            candidate_tasks=[
                Task(
                    task_id="drawing_task_layout_verify_001",
                    category=TaskCategory.GENERAL,
                    name=self._versioned_text(capture, "Verify layout and dimensions", 0.45),
                    point_a=self._versioned_text(
                        capture,
                        "Hand-drawn plan with ambiguous scale and dimensions.",
                        0.45,
                    ),
                    point_b=self._versioned_text(
                        capture,
                        "Confirmed measured layout suitable for pricing.",
                        0.45,
                    ),
                    step_number=1,
                    confidence=0.45,
                    provenance=[self._provenance(capture, confidence=0.45)],
                )
            ],
            clarifying_questions=[
                ClarifyingQuestion(
                    question="Confirm the measured room dimensions, wall positions, and opening widths.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="The hand-drawn floor plan does not provide reliable dimensions for pricing.",
                    related_task_ids=["drawing_task_layout_verify_001"],
                    rank=1,
                ),
                ClarifyingQuestion(
                    question="Confirm which drawn lines are existing walls, new partitions, or openings.",
                    severity=GapSeverity.MUST_HAVE,
                    reason="Semantic meaning of hand-drawn lines is ambiguous without site confirmation.",
                    related_task_ids=["drawing_task_layout_verify_001"],
                    rank=2,
                ),
            ],
            confidence=0.42,
        )

    def _provenance(self, capture: InputCapture, confidence: float) -> Provenance:
        return Provenance(
            modality=Modality.DRAWING,
            capture_id=capture.capture_id,
            extractor=self.extractor_name,
            confidence=confidence,
        )

    def _versioned_text(
        self,
        capture: InputCapture,
        value: str,
        confidence: float,
    ) -> VersionedField[str]:
        return VersionedField[str](
            value=value,
            confidence=confidence,
            provenance=[self._provenance(capture, confidence)],
        )
