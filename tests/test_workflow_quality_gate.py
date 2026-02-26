"""Workflow quality gate integration tests."""

import asyncio
import os
from pathlib import Path

import pytest

pytest.importorskip("temporalio")
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.worker.activities_execution import (
    activity_cmdb_validate,
    activity_cv_extract,
    activity_load_change,
    activity_persist_step_and_proofpack,
    activity_quality_gate,
    activity_set_scenario,
)
from apps.worker.workflows.change_execution_workflow import ChangeExecutionWorkflow, WorkflowInput
from packages.core.runtime import load_proofpack


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def set_scenario_a():
    os.environ["SCENARIO"] = "CHG-001_A"
    yield
    os.environ.pop("SCENARIO", None)


@pytest.fixture
def ensure_sample_images():
    """Ensure sample images exist."""
    img_dir = _repo_root() / "samples" / "images"
    for name in ("evid-good.jpg", "evid-blurry.jpg"):
        if not (img_dir / name).exists():
            pytest.skip("Run scripts/gen_sample_images.py first")
    yield


@pytest.mark.asyncio
async def test_quality_gate_blocks_bad_then_passes(ensure_sample_images) -> None:
    """Upload EVID-002-BADQUALITY for S1 => NEEDS_RETAKE without CV/CMDB; then EVID-001 => VERIFIED."""
    task_queue = "test-quality-gate"
    async with await WorkflowEnvironment.start_time_skipping() as env:
        client: Client = env.client
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChangeExecutionWorkflow],
            activities=[
                activity_load_change,
                activity_set_scenario,
                activity_quality_gate,
                activity_cv_extract,
                activity_cmdb_validate,
                activity_persist_step_and_proofpack,
            ],
        ):
            handle = await client.start_workflow(
                ChangeExecutionWorkflow.run,
                WorkflowInput(change_id="CHG-QG", scenario="CHG-001_A"),
                id="wf-quality-gate",
                task_queue=task_queue,
            )

            # S1: EVID-002-BADQUALITY (blurry) => should fail quality gate, NEEDS_RETAKE
            await handle.signal(ChangeExecutionWorkflow.evidence_uploaded, "S1", "EVID-002-BADQUALITY")
            await asyncio.sleep(0.5)

            # Check proofpack: S1 should be NEEDS_RETAKE with quality_gate tool_call, no CV
            proofpack = load_proofpack("CHG-QG")
            assert proofpack is not None
            s1_results = [s for s in proofpack.steps if s.step_id == "S1"]
            assert len(s1_results) >= 1
            s1 = s1_results[-1]
            assert s1.status.value == "needs_retake"
            tool_calls = s1.tool_calls or []
            qg_calls = [t for t in tool_calls if t.get("tool") == "quality_gate"]
            assert len(qg_calls) >= 1
            assert qg_calls[0].get("decision") == "needs_retake"
            # No CV tool calls (no read_port_label / read_cable_tag in tool_calls)
            cv_like = [t for t in tool_calls if "read_port" in str(t) or "read_cable" in str(t)]
            assert len(cv_like) == 0

            # S1: EVID-001 (good) => quality passes, CV runs, VERIFIED
            await handle.signal(ChangeExecutionWorkflow.evidence_uploaded, "S1", "EVID-001")
            await asyncio.sleep(0.5)

            # S2: no evidence required (action step)
            # S3: EVID-003 (good)
            await handle.signal(ChangeExecutionWorkflow.evidence_uploaded, "S3", "EVID-003")

            result = await handle.result()
            assert result["change_id"] == "CHG-QG"
            step_results = result.get("step_results", [])
            s1_final = next((s for s in step_results if s.get("step_id") == "S1"), None)
            assert s1_final is not None
            assert s1_final.get("status") == "verified"
