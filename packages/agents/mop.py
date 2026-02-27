"""MOP compliance agent: step -> technician prompt + evidence summary."""

from __future__ import annotations

from packages.core.models.steps import StepDefinition


def mop_advice(step_def: StepDefinition) -> dict:
    """Return tech_prompt and required_evidence_summary. Deterministic in mock."""
    evidence = step_def.evidence
    verify = step_def.verify
    if evidence and evidence.count > 0:
        kinds = []
        if verify and verify.requires_port_label:
            kinds.append("port label")
        if verify and verify.requires_cable_tag:
            kinds.append("cable tag")
        if not kinds:
            kinds = ["label/tag"]
        required = f"Photo of {', '.join(kinds)}"
    else:
        required = "No evidence required"
    tech_prompt = f"{step_def.description}. {required}."
    return {
        "tech_prompt": tech_prompt,
        "required_evidence_summary": required,
    }
