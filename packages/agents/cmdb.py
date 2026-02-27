"""CMDB validator agent: observed + NetBox -> proceed/block + escalation text."""

from __future__ import annotations

from typing import Any

from packages.core.models.steps import StepDefinition


def cmdb_advice(
    step_def: StepDefinition,
    cmdb_out: dict[str, Any],
) -> dict:
    """Return decision (proceed|block), reason, escalation_text. Deterministic."""
    match = cmdb_out.get("match", False)
    reason = cmdb_out.get("reason", "")
    if match:
        return {
            "decision": "proceed",
            "reason": reason or "CMDB mapping verified.",
            "escalation_text": None,
        }
    approval = step_def.approval
    needs_approval = approval and approval.required
    escalation_text = (
        f"CMDB mismatch for step {step_def.step_id}: {reason}. "
        + ("Approval required to override." if needs_approval else "")
    )
    return {
        "decision": "block",
        "reason": reason or "CMDB mismatch",
        "escalation_text": escalation_text,
    }
