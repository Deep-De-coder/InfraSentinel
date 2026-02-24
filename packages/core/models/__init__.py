"""Core domain models."""

from packages.core.models.change import ChangeRequest
from packages.core.models.legacy import (
    AuditEvent,
    ChangeStep,
    CVCableTagResult,
    CVPortLabelResult,
    EvidenceRef,
    ExpectedMapping,
    StepResultLegacy,
    StepStatusLegacy,
    StepTypeLegacy,
    ValidationResult,
)
StepStatus = StepStatusLegacy  # backward compat
StepType = StepTypeLegacy  # backward compat
from packages.core.models.proofpack import EvidenceRef as ProofPackEvidenceRef
from packages.core.models.proofpack import ProofPack, render_proofpack_json
from packages.core.models.steps import (
    ApprovalGate,
    EvidenceKind,
    EvidenceRequirement,
    StepDefinition,
    StepResult,
    StepStatus,
    StepType,
    VerificationRequirement,
)

__all__ = [
    "ApprovalGate",
    "ChangeRequest",
    "EvidenceKind",
    "EvidenceRequirement",
    "ProofPack",
    "ProofPackEvidenceRef",
    "StepDefinition",
    "StepResult",
    "StepStatus",
    "StepType",
    "VerificationRequirement",
    "render_proofpack_json",
]
