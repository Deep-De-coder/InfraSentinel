from pydantic import BaseModel

from packages.core.models import StepStatus


class MOPDecision(BaseModel):
    requires_evidence: bool
    required_evidence_types: list[str]
    gate: str


class VisionDecision(BaseModel):
    accept: bool
    guidance: str
    confidence: float


class CMDBDecision(BaseModel):
    status: StepStatus
    reason: str
    escalate: bool
