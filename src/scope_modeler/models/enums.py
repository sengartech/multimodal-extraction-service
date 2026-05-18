"""Shared enumerations for scope modeling."""

from __future__ import annotations

from enum import StrEnum


class Modality(StrEnum):
    TEXT = "text"
    PHOTO = "photo"
    DRAWING = "drawing"
    AUDIO = "audio"
    MANUAL = "manual"
    FUSION = "fusion"


class CaptureType(StrEnum):
    CONTRACTOR_NOTE = "contractor_note"
    FLOOR_PLAN = "floor_plan"
    SITE_PHOTO = "site_photo"
    AUDIO_RECORDING = "audio_recording"
    MANUAL_INPUT = "manual_input"
    DERIVED = "derived"


class GapSeverity(StrEnum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    IGNORE = "ignore"


class TaskCategory(StrEnum):
    DEMOLITION = "demolition"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    WATERPROOFING = "waterproofing"
    FLOORING = "flooring"
    WALLS = "walls"
    CEILING = "ceiling"
    PAINTING = "painting"
    CARPENTRY = "carpentry"
    MASONRY = "masonry"
    FACADE = "facade"
    GENERAL = "general"
    OTHER = "other"


class PricingReadinessStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"

