from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities import fetch_change, finalize_change, process_step
    from packages.core.models import StepType


class WorkflowInput(BaseModel):
    change_id: str


@dataclass
class WorkflowResult:
    change_id: str
    final_status: str
    proof_pack_id: str
    steps: list[dict]


@workflow.defn
class ChangeWorkflow:
    @workflow.run
    async def run(self, data: WorkflowInput) -> dict:
        change = await workflow.execute_activity(
            fetch_change,
            data.change_id,
            start_to_close_timeout=timedelta(seconds=20),
        )
        step_results: list[dict] = []
        for step in change["steps"]:
            evidence_id = None
            if step["step_type"] == StepType.VERIFY_PORT_AND_CABLE.value:
                evidence_id = "evidence-bad-port" if data.change_id.endswith("BLOCK") else "evidence-good"
            result = await workflow.execute_activity(
                process_step,
                args=[data.change_id, step, evidence_id],
                start_to_close_timeout=timedelta(seconds=20),
            )
            step_results.append(result)
            if result["status"] == "BLOCKED":
                break
        return await workflow.execute_activity(
            finalize_change,
            args=[data.change_id, step_results],
            start_to_close_timeout=timedelta(seconds=20),
        )
