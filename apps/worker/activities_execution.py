"""Activities for ChangeExecutionWorkflow."""

from __future__ import annotations

import cv2
import numpy as np
from opentelemetry import trace
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
from packages.core.fixtures.loaders import load_expected_mapping
from packages.core.runtime import (
    append_step_result_log,
    get_step_prompt,
    load_proofpack,
    read_evidence_registry,
    save_proofpack,
    save_step_prompt,
    set_scenario_config,
    write_approved_mapping,
)
from packages.core.vision.quality import compute_image_quality
from packages.cv.guidance import retake_guidance
from services.mcp_cv.handlers import CVHandlers
from services.mcp_netbox.handlers import NetboxHandlers
from services.mcp_ticketing.handlers import TicketingHandlers

_cv_handlers: CVHandlers | None = None
_netbox_handlers: NetboxHandlers | None = None
_ticketing_handlers: TicketingHandlers | None = None

_tracer = trace.get_tracer(__name__)


def configure_handlers(cv: CVHandlers, netbox: NetboxHandlers, ticketing: TicketingHandlers) -> None:
    global _cv_handlers, _netbox_handlers, _ticketing_handlers
    _cv_handlers = cv
    _netbox_handlers = netbox
    _ticketing_handlers = ticketing


async def _kafka_publish(topic: str, event: dict) -> None:
    """Fire-and-forget Kafka publish. Never raises."""
    try:
        from packages.core.kafka import get_kafka_bus

        bus = get_kafka_bus()
        if bus is not None:
            await bus.publish(topic, event)
    except Exception:
        pass


@activity.defn
async def activity_set_scenario(change_id: str, scenario: str) -> None:
    set_scenario_config(change_id, scenario)
    settings = get_settings()
    if settings.netbox_mode == "netbox":
        mapping = load_expected_mapping(change_id)
        write_approved_mapping(change_id, mapping)

    try:
        from packages.core.events import ChangeStartedEvent

        ev = ChangeStartedEvent(
            change_id=change_id,
            mop_id=scenario,
            technician_id="unknown",
            correlation_id=change_id,
        )
        await _kafka_publish("infrasentinel.change.started", ev.model_dump(mode="json"))
    except Exception:
        pass


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

    with _tracer.start_as_current_span("quality_gate") as span:
        metrics = compute_image_quality(
            img,
            blur_min=settings.blur_min,
            brightness_min=settings.brightness_min,
            glare_max=settings.glare_max,
            min_w=settings.min_width,
            min_h=settings.min_height,
        )
        span.set_attribute("quality.blur_score", metrics.blur_score)
        span.set_attribute("quality.brightness", metrics.brightness)
        span.set_attribute("quality.glare_score", metrics.glare_score)
        span.set_attribute("quality.is_too_blurry", metrics.is_too_blurry)
        span.set_attribute("quality.is_too_dark", metrics.is_too_dark)
        span.set_attribute("quality.is_too_glary", metrics.is_too_glary)
        span.set_attribute("quality.is_low_res", metrics.is_low_res)

        fail = metrics.is_too_blurry or metrics.is_too_dark or metrics.is_too_glary or metrics.is_low_res
        if fail:
            guidance = retake_guidance(metrics)
            try:
                from packages.core.events import QualityFailedEvent

                ev = QualityFailedEvent(
                    change_id=change_id,
                    step_id=step_id,
                    reason="Image quality below threshold",
                    metrics=metrics.model_dump(),
                    correlation_id=change_id,
                )
                await _kafka_publish("infrasentinel.quality.failed", ev.model_dump(mode="json"))
            except Exception:
                pass
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
async def activity_cv_extract(
    change_id: str, step_id: str, evidence_id: str, scenario: str
) -> tuple[dict, dict]:
    handlers = _cv_handlers or CVHandlers(scenario=scenario)

    with _tracer.start_as_current_span("ocr_extraction") as span:
        port = await handlers.read_port_label(evidence_id, change_id, scenario)
        tag = await handlers.read_cable_tag(evidence_id, change_id, scenario)
        raw_text = getattr(port, "raw_text", "") or ""
        span.set_attribute("ocr.raw_text_length", len(raw_text))
        span.set_attribute("ocr.port_confidence", port.confidence)
        span.set_attribute("ocr.tag_confidence", tag.confidence)

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
    global _netbox_handlers
    if _netbox_handlers is None:
        _netbox_handlers = NetboxHandlers()

    with _tracer.start_as_current_span("cmdb_validation") as span:
        out = await _netbox_handlers.validate_observed(change_id, panel_id, port_label, cable_tag)
        span.set_attribute("cmdb.match", out.match)
        span.set_attribute("cmdb.reason", out.reason or "")
        span.set_attribute("cmdb.confidence", out.confidence)

    if not out.match:
        try:
            from packages.core.events import CMDBMismatchEvent
            from packages.core.fixtures.loaders import load_expected_mapping

            mapping = load_expected_mapping(change_id)
            default = mapping.get("default", mapping)
            expected_str = (
                f"{default.get('panel_id', '')}:{default.get('port_label', '')}:"
                f"{default.get('cable_tag', '')}"
            )
            actual_str = f"{panel_id}:{port_label}:{cable_tag}"
            ev = CMDBMismatchEvent(
                change_id=change_id,
                step_id=f"{panel_id}:{port_label}",
                expected=expected_str,
                actual=actual_str,
                correlation_id=change_id,
            )
            await _kafka_publish("infrasentinel.cmdb.mismatch", ev.model_dump(mode="json"))
        except Exception:
            pass

    return {"match": out.match, "reason": out.reason, "confidence": out.confidence}


@activity.defn
async def activity_request_approval(
    change_id: str,
    step_id: str,
    reason: str,
    evidence_ids: list[str],
    escalation_text: str | None = None,
) -> dict:
    global _ticketing_handlers
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

    with _tracer.start_as_current_span("proofpack_persist") as span:
        append_step_result_log(result)
        proofpack = load_proofpack(change_id) or ProofPack(change_id=change_id)
        ev_ref = None
        if evidence_id:
            reg = read_evidence_registry(evidence_id)
            if reg:
                ev_ref = EvidenceRef(
                    evidence_id=evidence_id,
                    path=reg.get("object_key", f"evidence/{evidence_id}"),
                    uri=reg.get("uri"),
                    sha256=reg.get("sha256"),
                )
            else:
                ev_ref = EvidenceRef(evidence_id=evidence_id, path=f"evidence/{evidence_id}")
        updated = update_proofpack(proofpack, change_id, result, ev_ref)
        save_proofpack(updated)
        step_count = len(updated.steps) if updated.steps else 0
        span.set_attribute("proofpack.step_count", step_count)
        span.set_attribute("proofpack.change_id", change_id)

    try:
        from packages.core.events import StepCompletedEvent, ProofPackReadyEvent

        ocr_text = result.observed_port_label or result.observed_cable_tag or ""
        step_ev = StepCompletedEvent(
            change_id=change_id,
            step_id=result.step_id,
            status=result.status.value if hasattr(result.status, "value") else str(result.status),
            ocr_text=ocr_text,
            correlation_id=change_id,
        )
        await _kafka_publish("infrasentinel.step.completed", step_ev.model_dump(mode="json"))

        pp_ev = ProofPackReadyEvent(
            change_id=change_id,
            proof_pack_url=f"runtime/proofpacks/{change_id}.json",
            correlation_id=change_id,
        )
        await _kafka_publish("infrasentinel.proofpack.ready", pp_ev.model_dump(mode="json"))
    except Exception:
        pass
