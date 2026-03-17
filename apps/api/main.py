"""InfraSentinel API."""

from __future__ import annotations

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from temporalio.client import Client
from temporalio.exceptions import TemporalError, WorkflowAlreadyStartedError

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
from packages.core.runtime import (
    get_latest_step_result,
    get_step_prompt,
    load_proofpack,
    read_evidence_registry,
    write_evidence_registry,
)
from packages.core.storage import MinioEvidenceStore
from packages.core.vision.quality import compute_image_quality
from packages.cv.guidance import retake_guidance

app = FastAPI(title="InfraSentinel API")


def _require_api_key(x_infra_key: str | None = Header(None, alias="X-INFRA-KEY")) -> None:
    settings = get_settings()
    if not settings.infra_api_key:
        return
    if not x_infra_key or x_infra_key != settings.infra_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-INFRA-KEY")


def _require_read_auth(x_infra_key: str | None = Header(None, alias="X-INFRA-KEY")) -> None:
    settings = get_settings()
    if not settings.auth_reads:
        return
    if not settings.infra_api_key:
        return
    if not x_infra_key or x_infra_key != settings.infra_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-INFRA-KEY")


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
async def start_change(req: StartChangeRequest, _: None = Depends(_require_api_key)) -> StartChangeResponse:
    settings = get_settings()
    client = await get_temporal_client(settings)
    workflow_id = f"change-{req.change_id}"
    scenario = req.scenario or settings.scenario or "CHG-001_A"
    try:
        handle = await client.start_workflow(
            ChangeExecutionWorkflow.run,
            WorkflowInput(change_id=req.change_id, scenario=scenario),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
    except WorkflowAlreadyStartedError:
        raise HTTPException(
            status_code=409,
            detail=f"Change {req.change_id} already started. Run 'docker compose -f infra/docker-compose.yml --profile dev down' to reset, or use a different change_id.",
        )
    return StartChangeResponse(workflow_id=workflow_id, run_id=handle.result_run_id or "")


@app.post("/v1/evidence/upload")
async def upload_evidence(
    change_id: str = Form(...),
    step_id: str = Form(...),
    evidence_id: str | None = Form(None),
    file: UploadFile | None = File(None),
    _: None = Depends(_require_api_key),
):
    settings = get_settings()
    data: bytes
    if evidence_id:
        from packages.core.fixtures.evidence import get_evidence_bytes
        data = get_evidence_bytes(evidence_id, change_id, settings.local_evidence_dir)
        if not data:
            raise HTTPException(status_code=404, detail="Evidence not found")
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
        if isinstance(store, MinioEvidenceStore) and evidence.metadata:
            meta = evidence.metadata
            write_evidence_registry(out_id, {
                "object_key": meta.get("object_key", f"evidence/{change_id}/{out_id}.jpg"),
                "sha256": meta.get("sha256"),
                "uri": evidence.uri,
            })
    else:
        raise HTTPException(status_code=400, detail="Provide evidence_id or file")

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is not None:
        metrics = compute_image_quality(
            img,
            blur_min=settings.blur_min,
            brightness_min=settings.brightness_min,
            glare_max=settings.glare_max,
            min_w=settings.min_width,
            min_h=settings.min_height,
        )
        fail = metrics.is_too_blurry or metrics.is_too_dark or metrics.is_too_glary or metrics.is_low_res
        if fail:
            guidance = retake_guidance(metrics)
            return {
                "evidence_id": out_id,
                "status": "needs_retake",
                "message": "Image quality check failed. Please retake the photo.",
                "guidance": guidance,
                "quality": metrics.model_dump(),
            }

    client: Client = await get_temporal_client(settings)
    workflow_id = f"change-{change_id}"
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(ChangeExecutionWorkflow.evidence_uploaded, args=[step_id, out_id])
    except TemporalError as e:
        msg = str(e).lower()
        if "not found" in msg or "unknown" in msg or "does not exist" in msg or "workflow execution" in msg:
            raise HTTPException(
                status_code=404,
                detail="Change not started. Call POST /v1/changes/start first.",
            ) from e
        raise
    except Exception as e:
        msg = str(e).lower()
        if "not found" in msg or "unknown" in msg or "does not exist" in msg:
            raise HTTPException(
                status_code=404,
                detail="Change not started. Call POST /v1/changes/start first.",
            ) from e
        raise
    return {"evidence_id": out_id, "status": "verifying", "message": "Evidence received. Verifying..."}


@app.post("/v1/changes/{change_id}/approve")
async def approve_change(change_id: str, req: ApproveRequest, _: None = Depends(_require_api_key)) -> dict:
    client = await get_temporal_client(get_settings())
    workflow_id = f"change-{change_id}"
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(ChangeExecutionWorkflow.approval_granted, args=[req.step_id, req.approver])
    return {"ok": True, "change_id": change_id, "step_id": req.step_id}


@app.get("/v1/changes/{change_id}/steps/{step_id}/prompt")
async def get_step_prompt_endpoint(
    change_id: str, step_id: str, _: None = Depends(_require_read_auth)
) -> dict:
    """Get latest technician prompt for the step (from MOP agent)."""
    prompt = get_step_prompt(change_id, step_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Step prompt not found")
    return {"change_id": change_id, "step_id": step_id, "tech_prompt": prompt}


@app.get("/v1/changes/{change_id}/steps/{step_id}")
async def get_step(
    change_id: str, step_id: str, _: None = Depends(_require_read_auth)
) -> dict:
    result = get_latest_step_result(change_id, step_id)
    if not result:
        raise HTTPException(status_code=404, detail="Step result not found")
    return result


@app.get("/v1/changes/{change_id}/proofpack")
async def get_proofpack(
    change_id: str, _: None = Depends(_require_read_auth)
) -> dict:
    proofpack = load_proofpack(change_id)
    if not proofpack:
        raise HTTPException(status_code=404, detail="Proof pack not found")
    return proofpack.model_dump(mode="json")


@app.get("/v1/evidence/{evidence_id}")
async def get_evidence_url(evidence_id: str) -> dict:
    """Return presigned URL for evidence (dev only, when using MinIO)."""
    settings = get_settings()
    store = get_evidence_store(settings)
    if not isinstance(store, MinioEvidenceStore):
        raise HTTPException(status_code=404, detail="Evidence URL only available with MinIO backend")
    reg = read_evidence_registry(evidence_id)
    if not reg or not reg.get("object_key"):
        raise HTTPException(status_code=404, detail="Evidence not found")
    url = store.generate_presigned_url(reg["object_key"])
    return {"evidence_id": evidence_id, "url": url, "expires_in": 3600}


if __name__ == "__main__":
    import uvicorn

    cfg = get_settings()
    uvicorn.run(app, host=cfg.app_host, port=cfg.app_port)
