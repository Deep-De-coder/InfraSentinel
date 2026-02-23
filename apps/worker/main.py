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
from apps.worker.workflows.change_workflow import ChangeWorkflow
from packages.core.config import get_settings
from packages.core.db import build_engine, init_db, session_factory
from packages.core.observability import configure_observability


async def run_worker() -> None:
    settings = get_settings()
    settings.local_evidence_dir.mkdir(parents=True, exist_ok=True)
    configure_observability(settings)

    engine = build_engine(settings.database_url)
    await init_db(engine)
    configure_dependencies(WorkerDependencies(session_factory(engine)))

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ChangeWorkflow],
        activities=[fetch_change, process_step, finalize_change],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
