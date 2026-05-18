"""Generic versioned field support for mutable scope values."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.models.provenance import Provenance

T = TypeVar("T")


class VersionHistoryEntry(BaseModel, Generic[T]):
    """Prior value and reason for a mutable field change."""

    model_config = ConfigDict(extra="forbid")

    previous_value: T
    changed_at: datetime
    reason: str | None = None
    provenance: list[Provenance] = Field(default_factory=list)


class VersionedField(BaseModel, Generic[T]):
    """A value with confidence, provenance, and change history."""

    model_config = ConfigDict(extra="forbid")

    value: T
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: list[Provenance] = Field(default_factory=list)
    history: list[VersionHistoryEntry[T]] = Field(default_factory=list)

