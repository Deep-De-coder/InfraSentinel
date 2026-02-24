"""Proof pack update logic."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.core.models.proofpack import EvidenceRef, ProofPack
from packages.core.models.steps import StepResult, StepStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def update_proofpack(
    existing: ProofPack | None,
    change_id: str,
    step_result: StepResult,
    evidence_ref: EvidenceRef | None = None,
) -> ProofPack:
    """Add/update step result and evidence index."""
    steps = list(existing.steps) if existing else []
    evidence_index = list(existing.evidence_index) if existing else []
    started_at = existing.started_at if existing else utc_now()
    completed_at = existing.completed_at

    # Replace or append step result
    found = False
    for i, s in enumerate(steps):
        if s.step_id == step_result.step_id:
            steps[i] = step_result
            found = True
            break
    if not found:
        steps.append(step_result)

    # Add evidence if new
    if evidence_ref:
        seen = {e.evidence_id for e in evidence_index}
        if evidence_ref.evidence_id not in seen:
            evidence_index.append(evidence_ref)

    # Summary counts
    verified = sum(1 for s in steps if s.status == StepStatus.VERIFIED or s.status == StepStatus.OVERRIDDEN)
    blocked = sum(1 for s in steps if s.status == StepStatus.BLOCKED)
    retake = sum(1 for s in steps if s.status == StepStatus.NEEDS_RETAKE)
    all_done = all(
        s.status in (StepStatus.VERIFIED, StepStatus.OVERRIDDEN, StepStatus.BLOCKED, StepStatus.FAILED)
        for s in steps
    )
    if all_done:
        completed_at = utc_now()

    return ProofPack(
        change_id=change_id,
        started_at=started_at,
        completed_at=completed_at,
        summary={
            "verified_steps": verified,
            "blocked_steps": blocked,
            "retake_requests": retake,
            "total_steps": len(steps),
        },
        steps=steps,
        evidence_index=evidence_index,
    )
