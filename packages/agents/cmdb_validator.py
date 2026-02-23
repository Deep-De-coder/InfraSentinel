from __future__ import annotations

from packages.agents.models import CMDBDecision
from packages.core.models import StepStatus, ValidationResult


class CMDBValidatorAgent:
    async def run(self, validation: ValidationResult) -> CMDBDecision:
        if not validation.match:
            return CMDBDecision(
                status=StepStatus.BLOCKED,
                reason=f"CMDB mismatch: {validation.reason}",
                escalate=True,
            )
        if validation.confidence < 0.85:
            return CMDBDecision(
                status=StepStatus.BLOCKED,
                reason=f"Low validation confidence: {validation.confidence:.2f}",
                escalate=False,
            )
        return CMDBDecision(status=StepStatus.VERIFIED, reason="CMDB mapping verified.", escalate=False)
