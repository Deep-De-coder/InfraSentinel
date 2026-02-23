from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from temporalio.client import WorkflowHandle

from apps.api.deps import get_db_session_factory, get_evidence_store, get_temporal_client
from apps.api.schemas import StartChangeRequest, StartChangeResponse, UploadEvidenceResponse
from apps.worker.workflows.change_workflow import ChangeWorkflow, WorkflowInput
from packages.core.config import get_settings
from packages.core.observability import configure_observability

app = FastAPI(title="InfraSentinel API")


@app.on_event("startup")
async def startup() -> None:
    settings = get_settings()
    settings.local_evidence_dir.mkdir(parents=True, exist_ok=True)
    configure_observability(settings)
    await get_db_session_factory(settings)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/changes/start", response_model=StartChangeResponse)
async def start_change(req: StartChangeRequest) -> StartChangeResponse:
    settings = get_settings()
    client = await get_temporal_client(settings)
    workflow_id = f"change-{req.change_id}"
    handle: WorkflowHandle = await client.start_workflow(
        ChangeWorkflow.run,
        WorkflowInput(change_id=req.change_id),
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return StartChangeResponse(workflow_id=workflow_id, run_id=handle.run_id or "")


@app.post("/v1/evidence/upload", response_model=UploadEvidenceResponse)
async def upload_evidence(
    change_id: str = Form(...),
    step_id: str = Form(...),
    file: UploadFile = File(...),
) -> UploadEvidenceResponse:
    settings = get_settings()
    store = get_evidence_store(settings)
    data = await file.read()
    evidence = await store.put_bytes(
        data=data,
        filename=file.filename or "upload.bin",
        metadata={"change_id": change_id, "step_id": step_id},
    )
    return UploadEvidenceResponse(evidence=evidence)


if __name__ == "__main__":
    import uvicorn

    cfg = get_settings()
    uvicorn.run(app, host=cfg.app_host, port=cfg.app_port)
