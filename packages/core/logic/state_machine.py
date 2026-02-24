"""Step state machine transitions."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.core.logic.policy import DEFAULT_MIN_CONF, retake_guidance_from_quality
from packages.core.models.steps import (
    StepDefinition,
    StepResult,
    StepStatus,
    StepType,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def start_step(step_def: StepDefinition) -> StepStatus:
    """Initial status when step starts."""
    if step_def.evidence and step_def.evidence.count > 0:
        return StepStatus.AWAITING_EVIDENCE
    return StepStatus.VERIFYING


def on_evidence_uploaded(step_result: StepResult, evidence_id: str) -> StepResult:
    """Append evidence and transition to VERIFYING."""
    new_ids = list(step_result.evidence_ids) + [evidence_id]
    return StepResult(
        change_id=step_result.change_id,
        step_id=step_result.step_id,
        status=StepStatus.VERIFYING,
        evidence_ids=new_ids,
        observed_panel_id=step_result.observed_panel_id,
        observed_port_label=step_result.observed_port_label,
        observed_cable_tag=step_result.observed_cable_tag,
        confidence=step_result.confidence,
        cmdb_match=step_result.cmdb_match,
        cmdb_reason=step_result.cmdb_reason,
        guidance=step_result.guidance,
        notes=step_result.notes,
        tool_calls=step_result.tool_calls,
        approver=step_result.approver,
        created_at=step_result.created_at,
        updated_at=utc_now(),
    )


def apply_cv_result(
    step_def: StepDefinition,
    step_result: StepResult,
    port_out: object,
    tag_out: object,
    min_confidence: float = DEFAULT_MIN_CONF,
) -> StepResult:
    """Apply CV outputs; set NEEDS_RETAKE if low confidence or missing required fields."""
    verify = step_def.verify or __default_verify()
    guidance: list[str] = []
    observed_panel = getattr(port_out, "panel_id", None) or getattr(port_out, "port_label", None)
    observed_port = getattr(port_out, "port_label", None)
    observed_tag = getattr(tag_out, "cable_tag", None)
    port_conf = getattr(port_out, "confidence", 0.0) or 0.0
    tag_conf = getattr(tag_out, "confidence", 0.0) or 0.0

    needs_retake = False
    if verify.requires_port_label:
        if not observed_port or port_conf < min_confidence:
            needs_retake = True
            guidance.extend(retake_guidance_from_quality())
    if verify.requires_cable_tag:
        if not observed_tag or tag_conf < min_confidence:
            needs_retake = True
            guidance.extend(retake_guidance_from_quality())

    combined_conf = min(port_conf, tag_conf) if (verify.requires_port_label and verify.requires_cable_tag) else (port_conf or tag_conf)

    if needs_retake:
        return StepResult(
            change_id=step_result.change_id,
            step_id=step_result.step_id,
            status=StepStatus.NEEDS_RETAKE,
            evidence_ids=step_result.evidence_ids,
            observed_panel_id=str(observed_panel) if observed_panel else None,
            observed_port_label=str(observed_port) if observed_port else None,
            observed_cable_tag=str(observed_tag) if observed_tag else None,
            confidence=combined_conf,
            cmdb_match=step_result.cmdb_match,
            cmdb_reason=step_result.cmdb_reason,
            guidance=list(dict.fromkeys(guidance)),
            notes="Low confidence or missing required fields",
            tool_calls=step_result.tool_calls,
            approver=step_result.approver,
            created_at=step_result.created_at,
            updated_at=utc_now(),
        )

    return StepResult(
        change_id=step_result.change_id,
        step_id=step_result.step_id,
        status=StepStatus.VERIFYING,
        evidence_ids=step_result.evidence_ids,
        observed_panel_id=str(observed_panel) if observed_panel else None,
        observed_port_label=str(observed_port) if observed_port else None,
        observed_cable_tag=str(observed_tag) if observed_tag else None,
        confidence=combined_conf,
        cmdb_match=step_result.cmdb_match,
        cmdb_reason=step_result.cmdb_reason,
        guidance=[],
        notes=step_result.notes,
        tool_calls=step_result.tool_calls,
        approver=step_result.approver,
        created_at=step_result.created_at,
        updated_at=utc_now(),
    )


def __default_verify():
    from packages.core.models.steps import VerificationRequirement
    return VerificationRequirement(requires_port_label=True, requires_cable_tag=True)


def apply_cmdb_validation(
    step_def: StepDefinition,
    step_result: StepResult,
    cmdb_out: object,
) -> StepResult:
    """Apply CMDB validation; VERIFIED if match, else BLOCKED."""
    match = getattr(cmdb_out, "match", False)
    reason = getattr(cmdb_out, "reason", "")

    if match:
        return StepResult(
            change_id=step_result.change_id,
            step_id=step_result.step_id,
            status=StepStatus.VERIFIED,
            evidence_ids=step_result.evidence_ids,
            observed_panel_id=step_result.observed_panel_id,
            observed_port_label=step_result.observed_port_label,
            observed_cable_tag=step_result.observed_cable_tag,
            confidence=step_result.confidence,
            cmdb_match=True,
            cmdb_reason=reason,
            guidance=step_result.guidance,
            notes=step_result.notes,
            tool_calls=step_result.tool_calls,
            approver=step_result.approver,
            created_at=step_result.created_at,
            updated_at=utc_now(),
        )

    approval = step_def.approval or __default_approval()
    return StepResult(
        change_id=step_result.change_id,
        step_id=step_result.step_id,
        status=StepStatus.BLOCKED,
        evidence_ids=step_result.evidence_ids,
        observed_panel_id=step_result.observed_panel_id,
        observed_port_label=step_result.observed_port_label,
        observed_cable_tag=step_result.observed_cable_tag,
        confidence=step_result.confidence,
        cmdb_match=False,
        cmdb_reason=reason,
        guidance=step_result.guidance,
        notes=f"CMDB mismatch: {reason}" + (" (approval required)" if approval.required else ""),
        tool_calls=step_result.tool_calls,
        approver=step_result.approver,
        created_at=step_result.created_at,
        updated_at=utc_now(),
    )


def __default_approval():
    from packages.core.models.steps import ApprovalGate
    return ApprovalGate(required=True, on_blocked=True)


def approve_override(step_result: StepResult, approver: str) -> StepResult:
    """Set OVERRIDDEN with approver."""
    return StepResult(
        change_id=step_result.change_id,
        step_id=step_result.step_id,
        status=StepStatus.OVERRIDDEN,
        evidence_ids=step_result.evidence_ids,
        observed_panel_id=step_result.observed_panel_id,
        observed_port_label=step_result.observed_port_label,
        observed_cable_tag=step_result.observed_cable_tag,
        confidence=step_result.confidence,
        cmdb_match=step_result.cmdb_match,
        cmdb_reason=step_result.cmdb_reason,
        guidance=step_result.guidance,
        notes=f"Override approved by {approver}",
        tool_calls=step_result.tool_calls,
        approver=approver,
        created_at=step_result.created_at,
        updated_at=utc_now(),
    )
