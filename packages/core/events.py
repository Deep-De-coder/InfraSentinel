"""Pydantic event schemas for the InfraSentinel Kafka event bus."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _correlation_id() -> str:
    return str(uuid.uuid4())


class BaseEvent(BaseModel):
    correlation_id: str = Field(default_factory=_correlation_id)
    timestamp: datetime = Field(default_factory=_now)


class ChangeStartedEvent(BaseEvent):
    change_id: str
    mop_id: str
    technician_id: str


class StepCompletedEvent(BaseEvent):
    change_id: str
    step_id: str
    status: str
    ocr_text: str


class QualityFailedEvent(BaseEvent):
    change_id: str
    step_id: str
    reason: str
    metrics: dict


class CMDBMismatchEvent(BaseEvent):
    change_id: str
    step_id: str
    expected: str
    actual: str


class ProofPackReadyEvent(BaseEvent):
    change_id: str
    proof_pack_url: str
