"""Legacy models for backward compatibility."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StepTypeLegacy(str, Enum):
    VERIFY_PORT_AND_CABLE = "verify_port_and_cable"
    TASK = "task"


class StepStatusLegacy(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class EvidenceRef(BaseModel):
    evidence_id: str
    uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ChangeStep(BaseModel):
    step_id: str
    description: str
    step_type: StepTypeLegacy = StepTypeLegacy.TASK
    requires_evidence: bool = False


class ExpectedMapping(BaseModel):
    change_id: str
    panel_id: str
    port_label: str
    cable_tag: str


class CVPortLabelResult(BaseModel):
    panel_id: str
    port_label: str
    confidence: float


class CVCableTagResult(BaseModel):
    cable_tag: str
    confidence: float


class ValidationResult(BaseModel):
    match: bool
    reason: str
    confidence: float


class StepResultLegacy(BaseModel):
    change_id: str
    step_id: str
    status: StepStatusLegacy
    notes: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
    event_id: str
    change_id: str
    step_id: str | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
