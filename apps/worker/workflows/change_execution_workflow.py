"""Change execution workflow with signals for evidence and approval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities_execution import (
        activity_cmdb_advice,
        activity_cmdb_validate,
        activity_cv_extract,
        activity_get_mop_prompt,
        activity_load_change,
        activity_persist_step_and_proofpack,
        activity_quality_gate,
        activity_request_approval,
        activity_set_scenario,
        activity_vision_advice,
    )
    from packages.core.logic.proofpack import update_proofpack
    from packages.core.logic.state_machine import (
        apply_cmdb_validation,
        apply_cv_result,
        approve_override,
        on_evidence_uploaded,
        start_step,
    )
    from packages.core.models.proofpack import EvidenceRef, ProofPack
    from packages.core.models.steps import StepDefinition, StepResult, StepStatus


@dataclass
class WorkflowInput:
    change_id: str
    scenario: str = "CHG-001_A"


@workflow.defn
class ChangeExecutionWorkflow:
    def __init__(self) -> None:
        self._evidence_signal: dict[str, str] = {}
        self._approval_signal: dict[str, str] = {}
        self._current_step_info: dict = {}

    @workflow.signal
    async def evidence_uploaded(self, step_id: str, evidence_id: str) -> None:
        self._evidence_signal[step_id] = evidence_id

    @workflow.signal
    async def approval_granted(self, step_id: str, approver: str) -> None:
        self._approval_signal[step_id] = approver

    @workflow.query
    def get_current_step(self) -> dict:
        return getattr(self, "_current_step_info", {})

    @workflow.run
    async def run(self, data: WorkflowInput) -> dict:
        await workflow.execute_activity(
            activity_set_scenario,
            args=[data.change_id, data.scenario],
            start_to_close_timeout=timedelta(seconds=5),
        )
        change = await workflow.execute_activity(
            activity_load_change,
            data.change_id,
            start_to_close_timeout=timedelta(seconds=10),
        )
        steps_def = change["steps"]
        step_results: list[dict] = []

        for step_def in steps_def:
            step_id = step_def["step_id"]
            evidence = step_def.get("evidence")
            verify = step_def.get("verify")
            approval = step_def.get("approval")
            step_def_model = StepDefinition.model_validate(step_def)

            initial_status = start_step(step_def_model)
            step_result = StepResult(
                change_id=data.change_id,
                step_id=step_id,
                status=initial_status,
                evidence_ids=[],
            )
            self._current_step_info = {
                "change_id": data.change_id,
                "step_id": step_id,
                "status": step_result.status.value,
            }

            await workflow.execute_activity(
                activity_get_mop_prompt,
                args=[data.change_id, step_id, step_def],
                start_to_close_timeout=timedelta(seconds=10),
            )

            if initial_status == StepStatus.AWAITING_EVIDENCE:
                await workflow.wait_condition(
                    lambda s=step_id: s in self._evidence_signal,
                    timeout=timedelta(hours=1),
                )
                evidence_id = self._evidence_signal.pop(step_id, "")
                step_result = on_evidence_uploaded(step_result, evidence_id)

            if step_result.status == StepStatus.VERIFYING and verify:
                qgate = await workflow.execute_activity(
                    activity_quality_gate,
                    args=[data.change_id, step_id, evidence_id],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                if not qgate.get("pass"):
                    step_result = StepResult(
                        change_id=data.change_id,
                        step_id=step_id,
                        status=StepStatus.NEEDS_RETAKE,
                        evidence_ids=step_result.evidence_ids,
                        guidance=qgate.get("guidance", []),
                        quality=qgate.get("metrics"),
                        quality_fail_reason="Image quality below threshold",
                        tool_calls=[qgate.get("tool_call", {})],
                    )
                    await workflow.execute_activity(
                        activity_persist_step_and_proofpack,
                        args=[data.change_id, step_result.model_dump(mode="json"), evidence_id],
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                    step_results.append(step_result.model_dump(mode="json"))
                    while True:
                        await workflow.wait_condition(
                            lambda s=step_id: s in self._evidence_signal,
                            timeout=timedelta(hours=1),
                        )
                        evidence_id = self._evidence_signal.pop(step_id, "")
                        step_result = on_evidence_uploaded(step_result, evidence_id)
                        qgate = await workflow.execute_activity(
                            activity_quality_gate,
                            args=[data.change_id, step_id, evidence_id],
                            start_to_close_timeout=timedelta(seconds=10),
                        )
                        if qgate.get("pass"):
                            break
                        step_result = StepResult(
                            change_id=data.change_id,
                            step_id=step_id,
                            status=StepStatus.NEEDS_RETAKE,
                            evidence_ids=step_result.evidence_ids,
                            guidance=qgate.get("guidance", []),
                            quality=qgate.get("metrics"),
                            quality_fail_reason="Image quality below threshold",
                            tool_calls=step_result.tool_calls + [qgate.get("tool_call", {})],
                        )
                        await workflow.execute_activity(
                            activity_persist_step_and_proofpack,
                            args=[data.change_id, step_result.model_dump(mode="json"), evidence_id],
                            start_to_close_timeout=timedelta(seconds=10),
                        )
                        step_results.append(step_result.model_dump(mode="json"))

            if step_result.status == StepStatus.VERIFYING and verify:
                ev_id = step_result.evidence_ids[-1] if step_result.evidence_ids else ""
                port_out, tag_out = await workflow.execute_activity(
                    activity_cv_extract,
                    args=[data.change_id, step_id, ev_id, data.scenario],
                    start_to_close_timeout=timedelta(seconds=20),
                )

                class PortOut:
                    pass

                po = PortOut()
                po.panel_id = port_out.get("panel_id")
                po.port_label = port_out.get("port_label")
                po.confidence = port_out.get("confidence", 0)

                class TagOut:
                    pass

                to = TagOut()
                to.cable_tag = tag_out.get("cable_tag")
                to.confidence = tag_out.get("confidence", 0)

                step_result = apply_cv_result(step_def_model, step_result, po, to)
                if step_result.status == StepStatus.NEEDS_RETAKE:
                    vision_guidance = await workflow.execute_activity(
                        activity_vision_advice,
                        args=[
                            step_def,
                            qgate.get("metrics"),
                            {"panel_id": po.panel_id, "port_label": po.port_label, "confidence": po.confidence},
                            {"cable_tag": to.cable_tag, "confidence": to.confidence},
                        ],
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                    if vision_guidance:
                        step_result = step_result.model_copy(update={"guidance": vision_guidance})

                while step_result.status == StepStatus.NEEDS_RETAKE:
                    await workflow.wait_condition(
                        lambda s=step_id: s in self._evidence_signal,
                        timeout=timedelta(hours=1),
                    )
                    evidence_id = self._evidence_signal.pop(step_id, "")
                    step_result = on_evidence_uploaded(step_result, evidence_id)
                    port_out, tag_out = await workflow.execute_activity(
                        activity_cv_extract,
                        args=[data.change_id, step_id, evidence_id, data.scenario],
                        start_to_close_timeout=timedelta(seconds=20),
                    )
                    po = PortOut()
                    po.panel_id = port_out.get("panel_id")
                    po.port_label = port_out.get("port_label")
                    po.confidence = port_out.get("confidence", 0)
                    to = TagOut()
                    to.cable_tag = tag_out.get("cable_tag")
                    to.confidence = tag_out.get("confidence", 0)
                    step_result = apply_cv_result(step_def_model, step_result, po, to)
                    if step_result.status == StepStatus.NEEDS_RETAKE:
                        vision_guidance = await workflow.execute_activity(
                            activity_vision_advice,
                            args=[
                                step_def,
                                None,
                                {"panel_id": po.panel_id, "port_label": po.port_label, "confidence": po.confidence},
                                {"cable_tag": to.cable_tag, "confidence": to.confidence},
                            ],
                            start_to_close_timeout=timedelta(seconds=10),
                        )
                        if vision_guidance:
                            step_result = step_result.model_copy(update={"guidance": vision_guidance})

                if step_result.status == StepStatus.VERIFYING:
                    cmdb_out = await workflow.execute_activity(
                        activity_cmdb_validate,
                        args=[
                            data.change_id,
                            step_result.observed_panel_id or "",
                            step_result.observed_port_label or "",
                            step_result.observed_cable_tag or "",
                        ],
                        start_to_close_timeout=timedelta(seconds=10),
                    )

                    class CmdbOut:
                        pass

                    co = CmdbOut()
                    co.match = cmdb_out.get("match", False)
                    co.reason = cmdb_out.get("reason", "")

                    step_result = apply_cmdb_validation(step_def_model, step_result, co)
                    if (
                        step_result.status == StepStatus.BLOCKED
                        and approval
                        and approval.get("required")
                    ):
                        escalation_text = await workflow.execute_activity(
                            activity_cmdb_advice,
                            args=[step_def, {"match": co.match, "reason": co.reason}],
                            start_to_close_timeout=timedelta(seconds=10),
                        )
                        await workflow.execute_activity(
                            activity_request_approval,
                            args=[
                                data.change_id,
                                step_id,
                                step_result.cmdb_reason or "",
                                step_result.evidence_ids,
                                escalation_text,
                            ],
                            start_to_close_timeout=timedelta(seconds=5),
                        )
                        await workflow.wait_condition(
                            lambda s=step_id: s in self._approval_signal,
                            timeout=timedelta(hours=24),
                        )
                        approver = self._approval_signal.pop(step_id, "system")
                        step_result = approve_override(step_result, approver)

            elif initial_status == StepStatus.VERIFYING and not verify:
                step_result = StepResult(
                    change_id=data.change_id,
                    step_id=step_id,
                    status=StepStatus.VERIFIED,
                    notes="Non-verification step completed",
                )

            ev_id = step_result.evidence_ids[-1] if step_result.evidence_ids else None
            await workflow.execute_activity(
                activity_persist_step_and_proofpack,
                args=[data.change_id, step_result.model_dump(mode="json"), ev_id],
                start_to_close_timeout=timedelta(seconds=10),
            )
            step_results.append(step_result.model_dump(mode="json"))

            if step_result.status == StepStatus.BLOCKED and not (approval and approval.get("required")):
                break

        return {
            "change_id": data.change_id,
            "step_results": step_results,
            "proofpack_path": f"runtime/proofpacks/{data.change_id}.json",
        }
