"""Activities for ChangeExecutionWorkflow."""

from __future__ import annotations

import cv2
import numpy as np
from temporalio import activity

from packages.core.config import get_settings
from packages.core.fixtures.evidence import get_evidence_bytes
from packages.core.fixtures.loaders import load_change
from packages.core.logic.proofpack import update_proofpack
from packages.core.models.proofpack import EvidenceRef, ProofPack
from packages.core.models.steps import StepResult
from packages.core.runtime import (
    append_step_result_log,
    load_proofpack,
    save_proofpack,
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
    change_id: str, step_id: str, reason: str, evidence_ids: list[str]
) -> dict:
    if _ticketing_handlers is None:
        _ticketing_handlers = TicketingHandlers()
    return await _ticketing_handlers.request_approval(
        change_id=change_id, step_id=step_id, reason=reason, evidence_ids=evidence_ids
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
