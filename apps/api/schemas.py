from pydantic import BaseModel

from packages.core.models.legacy import EvidenceRef


class StartChangeRequest(BaseModel):
    change_id: str
    scenario: str | None = None


class StartChangeResponse(BaseModel):
    workflow_id: str
    run_id: str


class UploadEvidenceRequest(BaseModel):
    change_id: str
    step_id: str
    evidence_id: str | None = None


class UploadEvidenceResponse(BaseModel):
    evidence_id: str


class ApproveRequest(BaseModel):
    step_id: str
    approver: str
