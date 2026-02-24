from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from packages.agents.cmdb_validator import CMDBValidatorAgent
from packages.agents.mop_compliance import MOPComplianceAgent
from packages.agents.vision_verifier import VisionVerifierAgent
from packages.core.audit import make_audit_event
from packages.core.db import persist_audit_event, persist_step_result
from packages.core.models import (
    CVCableTagResult,
    CVPortLabelResult,
    ChangeStep,
    EvidenceRef,
    StepResult,
    StepStatus,
    StepType,
)
from packages.mcp.client import MCPToolRouter
from services.mcp_camera.handlers import CameraHandlers
from services.mcp_cv.handlers import CVHandlers
from services.mcp_netbox.handlers import NetboxHandlers
from services.mcp_ticketing.handlers import TicketingHandlers


class WorkerDependencies:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        camera = CameraHandlers()
        cv = CVHandlers()
        netbox = NetboxHandlers()
        ticketing = TicketingHandlers()
        self.tools = MCPToolRouter(
            camera_capture_frame=camera.capture_frame,
            camera_store_evidence=camera.store_evidence,
            cv_read_port_label=cv.read_port_label,
            cv_read_cable_tag=cv.read_cable_tag,
            netbox_get_expected_mapping=netbox.get_expected_mapping,
            netbox_validate_observed=netbox.validate_observed,
            ticketing_get_change=ticketing.get_change,
            ticketing_post_step_result=ticketing.post_step_result,
        )
        self.mop_agent = MOPComplianceAgent()
        self.vision_agent = VisionVerifierAgent()
        self.cmdb_agent = CMDBValidatorAgent()


deps: WorkerDependencies | None = None


def configure_dependencies(d: WorkerDependencies) -> None:
    global deps
    deps = d


@activity.defn
async def fetch_change(change_id: str) -> dict:
    if deps is None:
        raise RuntimeError("Worker dependencies not configured.")
    change = await deps.tools.get_change(change_id=change_id)
    return change.model_dump(mode="json")


@activity.defn
async def process_step(change_id: str, step: dict, evidence_id: str | None = None) -> dict:
    if deps is None:
        raise RuntimeError("Worker dependencies not configured.")
    step_type = StepType(step["step_type"])
    step_id = step["step_id"]

    if step_type != StepType.VERIFY_PORT_AND_CABLE:
        result = StepResult(
            change_id=change_id,
            step_id=step_id,
            status=StepStatus.COMPLETED,
            notes="Non-verification step auto-completed in scaffold.",
        )
        async with deps.session_factory() as session:
            await persist_step_result(session, result)
            await persist_audit_event(
                session,
                make_audit_event(
                    change_id=change_id,
                    step_id=step_id,
                    event_type="step_completed",
                    payload=result.model_dump(mode="json"),
                ),
            )
        return result.model_dump(mode="json")

    step_model = ChangeStep.model_validate(step)
    mop_decision = await deps.mop_agent.run(step=step_model)
    evidence = (
        await deps.tools.capture_frame(source="samples/images/.gitkeep")
        if evidence_id is None
        else EvidenceRef(evidence_id=evidence_id, uri=f"local://{evidence_id}", metadata={})
    )
    port = await deps.tools.read_port_label(evidence_id=evidence.evidence_id)
    cable = await deps.tools.read_cable_tag(evidence_id=evidence.evidence_id)
    port_core = CVPortLabelResult(
        panel_id=port.panel_id or "UNKNOWN",
        port_label=port.port_label or "UNKNOWN",
        confidence=port.confidence,
    )
    cable_core = CVCableTagResult(
        cable_tag=cable.cable_tag or "UNKNOWN",
        confidence=cable.confidence,
    )
    vision = await deps.vision_agent.run(port=port_core, cable=cable_core)
    if not vision.accept:
        result = StepResult(
            change_id=change_id,
            step_id=step_id,
            status=StepStatus.BLOCKED,
            notes=f"{vision.guidance} (confidence={vision.confidence:.2f})",
            evidence_refs=[evidence],
        )
    else:
        validation = await deps.tools.validate_observed(
            change_id=change_id,
            panel_id=port_core.panel_id,
            port_label=port_core.port_label,
            cable_tag=cable_core.cable_tag,
        )
        cmdb = await deps.cmdb_agent.run(validation=validation)
        result = StepResult(
            change_id=change_id,
            step_id=step_id,
            status=cmdb.status,
            notes=f"{cmdb.reason}; gate={mop_decision.gate}",
            evidence_refs=[evidence],
        )

    async with deps.session_factory() as session:
        await persist_step_result(session, result)
        await persist_audit_event(
            session,
            make_audit_event(
                change_id=change_id,
                step_id=step_id,
                event_type="step_result",
                payload=result.model_dump(mode="json"),
            ),
        )

    await deps.tools.post_step_result(
        change_id=change_id,
        step_id=step_id,
        status=result.status.value,
        evidence_refs=result.evidence_refs,
        notes=result.notes,
    )
    return result.model_dump(mode="json")


@activity.defn
async def finalize_change(change_id: str, step_results: list[dict]) -> dict:
    status = "VERIFIED"
    if any(item["status"] == StepStatus.BLOCKED.value for item in step_results):
        status = "BLOCKED"
    return {
        "change_id": change_id,
        "final_status": status,
        "proof_pack_id": str(uuid4()),
        "steps": step_results,
    }
