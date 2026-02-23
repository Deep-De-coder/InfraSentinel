from pydantic import BaseModel

from packages.core.models import EvidenceRef


class StartChangeRequest(BaseModel):
    change_id: str


class StartChangeResponse(BaseModel):
    workflow_id: str
    run_id: str


class UploadEvidenceResponse(BaseModel):
    evidence: EvidenceRef
