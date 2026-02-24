"""Proof pack schema and rendering."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from packages.core.models.steps import StepResult


class EvidenceRef(BaseModel):
    evidence_id: str
    uri: str | None = None
    path: str | None = None
    sha256: str | None = None
    timestamp: datetime | None = None


class ProofPack(BaseModel):
    change_id: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepResult] = Field(default_factory=list)
    evidence_index: list[EvidenceRef] = Field(default_factory=list)


def render_proofpack_json(proofpack: ProofPack) -> dict[str, Any]:
    return proofpack.model_dump(mode="json")
