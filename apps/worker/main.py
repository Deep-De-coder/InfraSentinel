from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from apps.worker.activities import (
    WorkerDependencies,
    configure_dependencies,
    fetch_change,
    finalize_change,
    process_step,
)
from apps.worker.activities_execution import (
    configure_handlers,
    activity_cmdb_validate,
    activity_cv_extract,
    activity_load_change,
    activity_persist_step_and_proofpack,
    activity_request_approval,
    activity_set_scenario,
)
from apps.worker.workflows.change_execution_workflow import ChangeExecutionWorkflow
from apps.worker.workflows.change_workflow import ChangeWorkflow
from packages.core.config import get_settings
from packages.core.db import build_engine, init_db, session_factory
from packages.core.observability import configure_observability
from services.mcp_cv.handlers import CVHandlers
from services.mcp_netbox.handlers import NetboxHandlers
from services.mcp_ticketing.handlers import TicketingHandlers


async def run_worker() -> None:
    settings = get_settings()
    settings.local_evidence_dir.mkdir(parents=True, exist_ok=True)
    configure_observability(settings)

    engine = build_engine(settings.database_url)
    await init_db(engine)
    configure_dependencies(WorkerDependencies(session_factory(engine)))
    configure_handlers(
        CVHandlers(scenario=settings.scenario),
        NetboxHandlers(),
        TicketingHandlers(),
    )

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ChangeWorkflow, ChangeExecutionWorkflow],
        activities=[
            fetch_change,
            process_step,
            finalize_change,
            activity_load_change,
            activity_set_scenario,
            activity_cv_extract,
            activity_cmdb_validate,
            activity_request_approval,
            activity_persist_step_and_proofpack,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
