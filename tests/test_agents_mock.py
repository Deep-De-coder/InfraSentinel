"""Unit tests for agent functions in mock mode."""

import os

import pytest

from packages.agents.cmdb import cmdb_advice
from packages.agents.mop import mop_advice
from packages.agents.vision import vision_advice
from packages.core.models.steps import (
    ApprovalGate,
    EvidenceKind,
    EvidenceRequirement,
    StepDefinition,
    StepType,
    VerificationRequirement,
)


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["LLM_PROVIDER"] = "mock"
    yield
    os.environ.pop("LLM_PROVIDER", None)


def test_mop_advice_with_evidence() -> None:
    step = StepDefinition(
        step_id="S1",
        description="Verify panel port",
        step_type=StepType.PORT_VERIFY,
        evidence=EvidenceRequirement(kind=EvidenceKind.PHOTO, count=1),
        verify=VerificationRequirement(requires_port_label=True, requires_cable_tag=True),
    )
    out = mop_advice(step)
    assert "tech_prompt" in out
    assert "required_evidence_summary" in out
    assert "port label" in out["required_evidence_summary"] or "Photo" in out["required_evidence_summary"]


def test_mop_advice_no_evidence() -> None:
    step = StepDefinition(
        step_id="S2",
        description="Complete cable move",
        step_type=StepType.ACTION,
        evidence=None,
        verify=None,
    )
    out = mop_advice(step)
    assert "No evidence required" in out["required_evidence_summary"]


def test_vision_advice_accept() -> None:
    step = StepDefinition(
        step_id="S1",
        description="Verify",
        step_type=StepType.PORT_VERIFY,
        verify=VerificationRequirement(requires_port_label=True, requires_cable_tag=True, min_confidence=0.75),
    )
    out = vision_advice(
        step,
        None,
        {"panel_id": "P1", "port_label": "24", "confidence": 0.9},
        {"cable_tag": "T1", "confidence": 0.9},
    )
    assert out["decision"] == "accept"
    assert "Evidence accepted" in out["guidance"][0]


def test_vision_advice_retake_low_confidence() -> None:
    step = StepDefinition(
        step_id="S1",
        description="Verify",
        step_type=StepType.PORT_VERIFY,
        verify=VerificationRequirement(requires_port_label=True, requires_cable_tag=True, min_confidence=0.75),
    )
    out = vision_advice(
        step,
        None,
        {"panel_id": "P1", "port_label": "24", "confidence": 0.5},
        {"cable_tag": "T1", "confidence": 0.5},
    )
    assert out["decision"] == "retake"
    assert len(out["guidance"]) > 0


def test_cmdb_advice_proceed() -> None:
    step = StepDefinition(step_id="S1", description="Verify", step_type=StepType.PORT_VERIFY)
    out = cmdb_advice(step, {"match": True, "reason": "OK"})
    assert out["decision"] == "proceed"
    assert out["escalation_text"] is None


def test_cmdb_advice_block() -> None:
    step = StepDefinition(
        step_id="S1",
        description="Verify",
        step_type=StepType.PORT_VERIFY,
        approval=ApprovalGate(required=True),
    )
    out = cmdb_advice(step, {"match": False, "reason": "Port 99 not in expected mapping"})
    assert out["decision"] == "block"
    assert "escalation_text" in out
    assert "S1" in (out["escalation_text"] or "")
