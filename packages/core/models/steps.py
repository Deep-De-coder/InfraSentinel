"""Canonical step schema and step result."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StepType(str, Enum):
    CHECK = "check"
    CAPTURE = "capture"
    PORT_VERIFY = "port_verify"
    CABLE_VERIFY = "cable_verify"
    ACTION = "action"
    APPROVAL = "approval"


class EvidenceKind(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"


class EvidenceRequirement(BaseModel):
    kind: EvidenceKind = EvidenceKind.PHOTO
    count: int = 1


class VerificationRequirement(BaseModel):
    requires_port_label: bool = False
    requires_cable_tag: bool = False
    min_confidence: float = 0.75


class ApprovalGate(BaseModel):
    required: bool = False
    on_blocked: bool = True


class StepDefinition(BaseModel):
    step_id: str
    description: str
    step_type: StepType = StepType.ACTION
    evidence: EvidenceRequirement | None = None
    verify: VerificationRequirement | None = None
    approval: ApprovalGate | None = None


class StepStatus(str, Enum):
    PENDING = "pending"
    AWAITING_EVIDENCE = "awaiting_evidence"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    NEEDS_RETAKE = "needs_retake"
    BLOCKED = "blocked"
    OVERRIDDEN = "overridden"
    FAILED = "failed"


class StepResult(BaseModel):
    change_id: str
    step_id: str
    status: StepStatus
    evidence_ids: list[str] = Field(default_factory=list)
    observed_panel_id: str | None = None
    observed_port_label: str | None = None
    observed_cable_tag: str | None = None
    confidence: float | None = None
    cmdb_match: bool | None = None
    cmdb_reason: str | None = None
    guidance: list[str] = Field(default_factory=list)
    notes: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    approver: str | None = None
    quality: dict[str, Any] | None = None
    quality_fail_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
