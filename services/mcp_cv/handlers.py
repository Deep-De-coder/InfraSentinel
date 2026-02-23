from __future__ import annotations

from packages.core.models import CVCableTagResult, CVPortLabelResult
from services.common import load_sample_json


class CVHandlers:
    async def read_port_label(self, evidence_id: str) -> CVPortLabelResult:
        data = load_sample_json("cv_outputs.json")
        item = data.get(evidence_id, data["default"])
        return CVPortLabelResult(
            panel_id=item["panel_id"],
            port_label=item["port_label"],
            confidence=item["port_confidence"],
        )

    async def read_cable_tag(self, evidence_id: str) -> CVCableTagResult:
        data = load_sample_json("cv_outputs.json")
        item = data.get(evidence_id, data["default"])
        return CVCableTagResult(cable_tag=item["cable_tag"], confidence=item["cable_confidence"])
