"""Pydantic models for the normalized input manifest."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scope_modeler.models.enums import CaptureType, Modality


class CustomerContext(BaseModel):
    """Customer and job context supplied by the upstream upload layer."""

    model_config = ConfigDict(extra="forbid")

    site_type: str | None = None
    location_hint: str | None = None
    requested_turnaround_minutes: int | None = Field(default=None, ge=0)


class InputCapture(BaseModel):
    """Single input capture described by the manifest."""

    model_config = ConfigDict(extra="forbid")

    capture_id: str
    capture_type: CaptureType
    modality: Modality
    path: Path
    language: str | None = None
    description: str | None = None


class InputManifest(BaseModel):
    """Normalized envelope for all captures associated with a job."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    received_at: datetime
    locale: str
    customer_context: CustomerContext
    captures: list[InputCapture] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_capture_ids_are_unique(self) -> "InputManifest":
        capture_ids = [capture.capture_id for capture in self.captures]
        duplicate_ids = sorted(
            capture_id for capture_id in set(capture_ids) if capture_ids.count(capture_id) > 1
        )
        if duplicate_ids:
            raise ValueError(f"Duplicate capture IDs: {', '.join(duplicate_ids)}")
        return self

    def get_capture(self, capture_id: str) -> InputCapture | None:
        return next(
            (capture for capture in self.captures if capture.capture_id == capture_id),
            None,
        )

    def captures_by_modality(self, modality: Modality) -> list[InputCapture]:
        return [capture for capture in self.captures if capture.modality == modality]

    def missing_local_files(self, base_dir: str | Path = ".") -> list[Path]:
        missing_paths: list[Path] = []
        root = Path(base_dir)
        for capture in self.captures:
            manifest_path = capture.path
            local_path = manifest_path if manifest_path.is_absolute() else root / manifest_path
            if not local_path.exists():
                missing_paths.append(manifest_path)
        return missing_paths


def load_manifest(path: str | Path) -> InputManifest:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return InputManifest.model_validate(data)
