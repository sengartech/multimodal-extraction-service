"""Placeholder schema module for future ScopeBrief / Job models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScaffoldModel(BaseModel):
    """Tiny model used only to verify Pydantic v2 wiring in the scaffold."""

    model_config = ConfigDict(extra="forbid")

    name: str

