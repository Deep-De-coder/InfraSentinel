"""Vision verifier agent: CV outputs + quality -> accept/retake + guidance."""

from __future__ import annotations

from typing import Any

from packages.core.models.steps import StepDefinition


def vision_advice(
    step_def: StepDefinition,
    quality_metrics: dict[str, Any] | None,
    cv_port_out: dict[str, Any],
    cv_tag_out: dict[str, Any],
    min_confidence: float = 0.75,
) -> dict:
    """Return decision (accept|retake), guidance, confidence_summary. Deterministic."""
    port_conf = cv_port_out.get("confidence", 0.0) or 0.0
    tag_conf = cv_tag_out.get("confidence", 0.0) or 0.0
    verify = step_def.verify
    min_conf = (verify.min_confidence if verify else min_confidence) or min_confidence
    combined = min(port_conf, tag_conf) if (verify and verify.requires_port_label and verify.requires_cable_tag) else (port_conf or tag_conf)

    guidance: list[str] = []
    decision = "accept"

    if quality_metrics:
        if quality_metrics.get("is_too_blurry"):
            guidance.append("Hold steady and tap to focus; avoid motion.")
            decision = "retake"
        if quality_metrics.get("is_too_dark"):
            guidance.append("Increase lighting / enable flashlight.")
            decision = "retake"
        if quality_metrics.get("is_too_glary"):
            guidance.append("Change angle to reduce glare; avoid direct reflections.")
            decision = "retake"
        if quality_metrics.get("is_low_res"):
            guidance.append("Move closer; fill the frame with the label/tag.")
            decision = "retake"

    if combined < min_conf:
        decision = "retake"
        if not guidance:
            guidance.extend([
                "Move closer and fill the frame with the label",
                "Reduce glare / change angle",
                "Tap to focus / hold steady",
            ])

    if decision == "accept":
        guidance = ["Evidence accepted."]

    return {
        "decision": decision,
        "guidance": guidance[:4],
        "confidence_summary": f"port={port_conf:.2f} tag={tag_conf:.2f}",
    }
