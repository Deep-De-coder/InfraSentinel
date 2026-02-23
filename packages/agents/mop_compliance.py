from __future__ import annotations

from packages.agents.models import MOPDecision
from packages.core.models import ChangeStep, StepType


class MOPComplianceAgent:
    async def run(self, step: ChangeStep) -> MOPDecision:
        if step.step_type == StepType.VERIFY_PORT_AND_CABLE:
            return MOPDecision(
                requires_evidence=True,
                required_evidence_types=["panel_port_label", "cable_tag"],
                gate="verify_before_proceed",
            )
        return MOPDecision(
            requires_evidence=False,
            required_evidence_types=[],
            gate="no_additional_gate",
        )
