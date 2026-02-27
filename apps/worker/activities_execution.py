"""Activities for ChangeExecutionWorkflow."""

from __future__ import annotations

import cv2
import numpy as np
from temporalio import activity

from packages.a2a.client import A2AClient
from packages.agents.cmdb import cmdb_advice
from packages.agents.mop import mop_advice
from packages.agents.vision import vision_advice
from packages.core.config import get_settings
from packages.core.fixtures.evidence import get_evidence_bytes
from packages.core.fixtures.loaders import load_change
from packages.core.logic.proofpack import update_proofpack
from packages.core.models.proofpack import EvidenceRef, ProofPack
from packages.core.models.steps import StepDefinition, StepResult
from packages.core.runtime import (
    append_step_result_log,
    get_step_prompt,
    load_proofpack,
    save_proofpack,
    save_step_prompt,
    set_scenario_config,
)
from packages.core.vision.quality import compute_image_quality
from packages.cv.guidance import retake_guidance
from services.mcp_cv.handlers import CVHandlers
from services.mcp_netbox.handlers import NetboxHandlers
from services.mcp_ticketing.handlers import TicketingHandlers

_cv_handlers: CVHandlers | None = None
_netbox_handlers: NetboxHandlers | None = None
_ticketing_handlers: TicketingHandlers | None = None


def configure_handlers(cv: CVHandlers, netbox: NetboxHandlers, ticketing: TicketingHandlers) -> None:
    global _cv_handlers, _netbox_handlers, _ticketing_handlers
    _cv_handlers = cv
    _netbox_handlers = netbox
    _ticketing_handlers = ticketing


@activity.defn
async def activity_quality_gate(
    change_id: str,
    step_id: str,
    evidence_id: str,
) -> dict:
    """Compute quality metrics. Returns pass, metrics, guidance, tool_call."""
    settings = get_settings()
    data = get_evidence_bytes(
        evidence_id,
        change_id=change_id,
        local_evidence_dir=settings.local_evidence_dir,
    )
    if not data:
        return {
            "pass": False,
            "metrics": None,
            "guidance": ["Evidence file not found; please upload again."],
            "tool_call": {"tool": "quality_gate", "error": "evidence_not_found", "decision": "needs_retake"},
        }
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {
            "pass": False,
            "metrics": None,
            "guidance": ["Invalid image; please upload a valid photo."],
            "tool_call": {"tool": "quality_gate", "error": "decode_failed", "decision": "needs_retake"},
        }
    metrics = compute_image_quality(
        img,
        blur_min=settings.blur_min,
        brightness_min=settings.brightness_min,
        glare_max=settings.glare_max,
        min_w=settings.min_width,
        min_h=settings.min_height,
    )
    fail = metrics.is_too_blurry or metrics.is_too_dark or metrics.is_too_glary or metrics.is_low_res
    if fail:
        guidance = retake_guidance(metrics)
        return {
            "pass": False,
            "metrics": metrics.model_dump(),
            "guidance": guidance,
            "tool_call": {
                "tool": "quality_gate",
                "metrics": metrics.model_dump(),
                "decision": "needs_retake",
            },
        }
    return {
        "pass": True,
        "metrics": metrics.model_dump(),
        "guidance": [],
        "tool_call": {"tool": "quality_gate", "metrics": metrics.model_dump(), "decision": "pass"},
    }


@activity.defn
async def activity_get_mop_prompt(change_id: str, step_id: str, step_def: dict) -> str:
    """Get technician prompt from MOP agent (or local). Store in runtime."""
    settings = get_settings()
    step_def_model = StepDefinition.model_validate(step_def)
    if settings.a2a_mode == "http":
        try:
            client = A2AClient(settings.a2a_mop_url)
            resp = await client.send_async("mop", {"step_def": step_def}, {})
            out = resp.output or {}
            tech_prompt = out.get("tech_prompt", step_def_model.description)
        except Exception:
            tech_prompt = mop_advice(step_def_model).get("tech_prompt", step_def_model.description)
    else:
        tech_prompt = mop_advice(step_def_model).get("tech_prompt", step_def_model.description)
    save_step_prompt(change_id, step_id, tech_prompt)
    return tech_prompt


@activity.defn
async def activity_vision_advice(
    step_def: dict,
    quality_metrics: dict | None,
    cv_port_out: dict,
    cv_tag_out: dict,
) -> list[str]:
    """Get guidance from Vision agent (or local). Worker keeps decision logic."""
    settings = get_settings()
    step_def_model = StepDefinition.model_validate(step_def)
    if settings.a2a_mode == "http":
        try:
            client = A2AClient(settings.a2a_vision_url)
            resp = await client.send_async(
                "vision",
                {
                    "step_def": step_def,
                    "quality_metrics": quality_metrics,
                    "cv_port_out": cv_port_out,
                    "cv_tag_out": cv_tag_out,
                },
                {},
            )
            out = resp.output or {}
            return out.get("guidance", [])
        except Exception:
            pass
    out = vision_advice(step_def_model, quality_metrics, cv_port_out, cv_tag_out)
    return out.get("guidance", [])


@activity.defn
async def activity_cmdb_advice(step_def: dict, cmdb_out: dict) -> str | None:
    """Get escalation text from CMDB agent (or local)."""
    settings = get_settings()
    step_def_model = StepDefinition.model_validate(step_def)
    if settings.a2a_mode == "http":
        try:
            client = A2AClient(settings.a2a_cmdb_url)
            resp = await client.send_async(
                "cmdb",
                {"step_def": step_def, "cmdb_out": cmdb_out},
                {},
            )
            out = resp.output or {}
            return out.get("escalation_text")
        except Exception:
            pass
    out = cmdb_advice(step_def_model, cmdb_out)
    return out.get("escalation_text")


@activity.defn
async def activity_load_change(change_id: str) -> dict:
    change = load_change(change_id)
    return change.model_dump(mode="json")


@activity.defn
async def activity_set_scenario(change_id: str, scenario: str) -> None:
    set_scenario_config(change_id, scenario)


@activity.defn
async def activity_cv_extract(
    change_id: str, step_id: str, evidence_id: str, scenario: str
) -> tuple[dict, dict]:
    handlers = _cv_handlers or CVHandlers(scenario=scenario)
    port = await handlers.read_port_label(evidence_id, change_id, scenario)
    tag = await handlers.read_cable_tag(evidence_id, change_id, scenario)
    return (
        {
            "panel_id": port.panel_id,
            "port_label": port.port_label,
            "confidence": port.confidence,
        },
        {"cable_tag": tag.cable_tag, "confidence": tag.confidence},
    )


@activity.defn
async def activity_cmdb_validate(
    change_id: str, panel_id: str, port_label: str, cable_tag: str
) -> dict:
    if _netbox_handlers is None:
        _netbox_handlers = NetboxHandlers()
    out = await _netbox_handlers.validate_observed(change_id, panel_id, port_label, cable_tag)
    return {"match": out.match, "reason": out.reason, "confidence": out.confidence}


@activity.defn
async def activity_request_approval(
    change_id: str,
    step_id: str,
    reason: str,
    evidence_ids: list[str],
    escalation_text: str | None = None,
) -> dict:
    if _ticketing_handlers is None:
        _ticketing_handlers = TicketingHandlers()
    return await _ticketing_handlers.request_approval(
        change_id=change_id,
        step_id=step_id,
        reason=reason,
        evidence_ids=evidence_ids,
        escalation_text=escalation_text,
    )


@activity.defn
async def activity_persist_step_and_proofpack(
    change_id: str, step_result: dict, evidence_id: str | None
) -> None:
    result = StepResult.model_validate(step_result)
    append_step_result_log(result)
    proofpack = load_proofpack(change_id) or ProofPack(change_id=change_id)
    ev_ref = (
        EvidenceRef(evidence_id=evidence_id, path=f"evidence/{evidence_id}")
        if evidence_id
        else None
    )
    updated = update_proofpack(proofpack, change_id, result, ev_ref)
    save_proofpack(updated)
