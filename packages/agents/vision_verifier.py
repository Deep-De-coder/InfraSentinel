from __future__ import annotations

from packages.agents.models import VisionDecision
from packages.core.models import CVCableTagResult, CVPortLabelResult


class VisionVerifierAgent:
    async def run(self, port: CVPortLabelResult, cable: CVCableTagResult) -> VisionDecision:
        confidence = min(port.confidence, cable.confidence)
        if confidence < 0.8:
            return VisionDecision(
                accept=False,
                guidance="Retake photo closer to panel/label; ensure tags are visible.",
                confidence=confidence,
            )
        return VisionDecision(accept=True, guidance="Evidence accepted.", confidence=confidence)
