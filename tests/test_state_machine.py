"""State machine transition tests."""

from packages.core.logic.state_machine import (
    apply_cmdb_validation,
    apply_cv_result,
    approve_override,
    on_evidence_uploaded,
    start_step,
)
from packages.core.models.steps import (
    ApprovalGate,
    EvidenceRequirement,
    StepDefinition,
    StepResult,
    StepStatus,
    StepType,
    VerificationRequirement,
)


def test_start_step_awaiting_evidence_when_evidence_required() -> None:
    step_def = StepDefinition(
        step_id="S1",
        description="Verify port",
        step_type=StepType.PORT_VERIFY,
        evidence=EvidenceRequirement(count=1),
        verify=VerificationRequirement(requires_port_label=True, requires_cable_tag=True),
    )
    assert start_step(step_def) == StepStatus.AWAITING_EVIDENCE


def test_start_step_verifying_when_no_evidence() -> None:
    step_def = StepDefinition(
        step_id="S2",
        description="Action",
        step_type=StepType.ACTION,
        evidence=None,
    )
    assert start_step(step_def) == StepStatus.VERIFYING


def test_on_evidence_uploaded_appends_and_transitions() -> None:
    result = StepResult(change_id="CHG-001", step_id="S1", status=StepStatus.AWAITING_EVIDENCE)
    updated = on_evidence_uploaded(result, "EVID-001")
    assert updated.evidence_ids == ["EVID-001"]
    assert updated.status == StepStatus.VERIFYING


def test_apply_cv_result_low_confidence_needs_retake() -> None:
    class PortOut:
        panel_id = "PANEL-A"
        port_label = "24"
        confidence = 0.5

    class TagOut:
        cable_tag = "MDF-01-R12-P24"
        confidence = 0.6

    step_def = StepDefinition(
        step_id="S1",
        description="Verify",
        step_type=StepType.PORT_VERIFY,
        verify=VerificationRequirement(requires_port_label=True, requires_cable_tag=True),
    )
    result = StepResult(
        change_id="CHG-001",
        step_id="S1",
        status=StepStatus.VERIFYING,
        evidence_ids=["EVID-001"],
    )
    out = apply_cv_result(step_def, result, PortOut(), TagOut())
    assert out.status == StepStatus.NEEDS_RETAKE
    assert len(out.guidance) > 0


def test_apply_cv_result_high_confidence_verifying() -> None:
    class PortOut:
        panel_id = "PANEL-A"
        port_label = "24"
        confidence = 0.95

    class TagOut:
        cable_tag = "MDF-01-R12-P24"
        confidence = 0.96

    step_def = StepDefinition(
        step_id="S1",
        description="Verify",
        step_type=StepType.PORT_VERIFY,
        verify=VerificationRequirement(requires_port_label=True, requires_cable_tag=True),
    )
    result = StepResult(
        change_id="CHG-001",
        step_id="S1",
        status=StepStatus.VERIFYING,
        evidence_ids=["EVID-001"],
    )
    out = apply_cv_result(step_def, result, PortOut(), TagOut())
    assert out.status == StepStatus.VERIFYING
    assert out.observed_port_label == "24"


def test_apply_cmdb_validation_mismatch_blocked() -> None:
    class CmdbOut:
        match = False
        reason = "Expected A-24, got A-99"

    step_def = StepDefinition(
        step_id="S1",
        description="Verify",
        step_type=StepType.PORT_VERIFY,
        approval=ApprovalGate(required=True, on_blocked=True),
    )
    result = StepResult(
        change_id="CHG-001",
        step_id="S1",
        status=StepStatus.VERIFYING,
        evidence_ids=["EVID-001"],
        observed_port_label="A-99",
    )
    out = apply_cmdb_validation(step_def, result, CmdbOut())
    assert out.status == StepStatus.BLOCKED
    assert out.cmdb_match is False


def test_apply_cmdb_validation_match_verified() -> None:
    class CmdbOut:
        match = True
        reason = "OK"

    step_def = StepDefinition(step_id="S1", description="Verify", step_type=StepType.PORT_VERIFY)
    result = StepResult(
        change_id="CHG-001",
        step_id="S1",
        status=StepStatus.VERIFYING,
        evidence_ids=["EVID-001"],
    )
    out = apply_cmdb_validation(step_def, result, CmdbOut())
    assert out.status == StepStatus.VERIFIED
    assert out.cmdb_match is True


def test_approve_override() -> None:
    result = StepResult(
        change_id="CHG-001",
        step_id="S1",
        status=StepStatus.BLOCKED,
        evidence_ids=["EVID-001"],
    )
    out = approve_override(result, "admin@example.com")
    assert out.status == StepStatus.OVERRIDDEN
    assert out.approver == "admin@example.com"
