"""InfraSentinel API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from temporalio.client import Client

from apps.api.deps import get_db_session_factory, get_evidence_store, get_temporal_client
from apps.api.schemas import (
    ApproveRequest,
    StartChangeRequest,
    StartChangeResponse,
    UploadEvidenceResponse,
)
from apps.worker.workflows.change_execution_workflow import ChangeExecutionWorkflow, WorkflowInput
from packages.core.config import get_settings
from packages.core.observability import configure_observability
from packages.core.runtime import load_proofpack

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
    scenario = req.scenario or settings.scenario or "CHG-001_A"
    handle = await client.start_workflow(
        ChangeExecutionWorkflow.run,
        WorkflowInput(change_id=req.change_id, scenario=scenario),
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return StartChangeResponse(workflow_id=workflow_id, run_id=handle.result_run_id or "")


@app.post("/v1/evidence/upload", response_model=UploadEvidenceResponse)
async def upload_evidence(
    change_id: str = Form(...),
    step_id: str = Form(...),
    evidence_id: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> UploadEvidenceResponse:
    settings = get_settings()
    if evidence_id:
        out_id = evidence_id
    elif file and file.filename:
        store = get_evidence_store(settings)
        data = await file.read()
        evidence = await store.put_bytes(
            data=data,
            filename=file.filename,
            metadata={"change_id": change_id, "step_id": step_id},
        )
        out_id = evidence.evidence_id
    else:
        raise HTTPException(status_code=400, detail="Provide evidence_id or file")

    client: Client = await get_temporal_client(settings)
    workflow_id = f"change-{change_id}"
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(ChangeExecutionWorkflow.evidence_uploaded, step_id, out_id)
    return UploadEvidenceResponse(evidence_id=out_id)


@app.post("/v1/changes/{change_id}/approve")
async def approve_change(change_id: str, req: ApproveRequest) -> dict:
    client = await get_temporal_client(get_settings())
    workflow_id = f"change-{change_id}"
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(ChangeExecutionWorkflow.approval_granted, req.step_id, req.approver)
    return {"ok": True, "change_id": change_id, "step_id": req.step_id}


@app.get("/v1/changes/{change_id}/proofpack")
async def get_proofpack(change_id: str) -> dict:
    proofpack = load_proofpack(change_id)
    if not proofpack:
        raise HTTPException(status_code=404, detail="Proof pack not found")
    return proofpack.model_dump(mode="json")


if __name__ == "__main__":
    import uvicorn

    cfg = get_settings()
    uvicorn.run(app, host=cfg.app_host, port=cfg.app_port)
