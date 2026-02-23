from pydantic import BaseModel, Field

from packages.core.models import (
    CVCableTagResult,
    CVPortLabelResult,
    ChangeRequest,
    EvidenceRef,
    ExpectedMapping,
    StepStatus,
)


class CameraCaptureFrameInput(BaseModel):
    source: str


class CameraStoreEvidenceInput(BaseModel):
    path: str | None = None
    data_b64: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class CVReadPortLabelInput(BaseModel):
    evidence_id: str


class CVReadCableTagInput(BaseModel):
    evidence_id: str


class NetboxExpectedMappingInput(BaseModel):
    change_id: str


class NetboxValidateObservedInput(BaseModel):
    change_id: str
    panel_id: str
    port_label: str
    cable_tag: str


class TicketingGetChangeInput(BaseModel):
    change_id: str


class TicketingPostStepResultInput(BaseModel):
    change_id: str
    step_id: str
    status: StepStatus
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    notes: str | None = None


class TicketingPostStepResultOutput(BaseModel):
    ok: bool = True


ToolOutput = (
    EvidenceRef
    | CVCableTagResult
    | CVPortLabelResult
    | ExpectedMapping
    | ChangeRequest
    | TicketingPostStepResultOutput
)
