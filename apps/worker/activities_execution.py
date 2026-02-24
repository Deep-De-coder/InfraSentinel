"""Activities for ChangeExecutionWorkflow."""

from __future__ import annotations

from temporalio import activity

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
