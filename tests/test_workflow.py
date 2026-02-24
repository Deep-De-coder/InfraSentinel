from datetime import timedelta

import pytest

pytest.importorskip("temporalio")
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.worker.activities import (
    WorkerDependencies,
    configure_dependencies,
    fetch_change,
    finalize_change,
    process_step,
)
from apps.worker.workflows.change_workflow import ChangeWorkflow, WorkflowInput
from packages.core.db import build_engine, init_db, session_factory


@pytest.mark.asyncio
async def test_change_workflow_happy_path(tmp_path) -> None:
    engine = build_engine(f"sqlite+aiosqlite:///{tmp_path}/happy.db")
    await init_db(engine)
    configure_dependencies(WorkerDependencies(session_factory(engine)))

    async with await WorkflowEnvironment.start_time_skipping() as env:
        client: Client = env.client
        async with Worker(
            client,
            task_queue="test-queue",
            workflows=[ChangeWorkflow],
            activities=[fetch_change, process_step, finalize_change],
        ):
            result = await client.execute_workflow(
                ChangeWorkflow.run,
                WorkflowInput(change_id="CHG-1001"),
                id="wf-happy",
                task_queue="test-queue",
                execution_timeout=timedelta(seconds=30),
            )
    assert result["final_status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_change_workflow_block_path(tmp_path) -> None:
    engine = build_engine(f"sqlite+aiosqlite:///{tmp_path}/block.db")
    await init_db(engine)
    configure_dependencies(WorkerDependencies(session_factory(engine)))

    async with await WorkflowEnvironment.start_time_skipping() as env:
        client: Client = env.client
        async with Worker(
            client,
            task_queue="test-queue-2",
            workflows=[ChangeWorkflow],
            activities=[fetch_change, process_step, finalize_change],
        ):
            result = await client.execute_workflow(
                ChangeWorkflow.run,
                WorkflowInput(change_id="CHG-BLOCK"),
                id="wf-block",
                task_queue="test-queue-2",
                execution_timeout=timedelta(seconds=30),
            )
    assert result["final_status"] == "BLOCKED"
