from __future__ import annotations

from packages.core.models import ChangeRequest, StepStatus
from services.common import load_sample_json


class TicketingHandlers:
    async def get_change(self, change_id: str) -> ChangeRequest:
        data = load_sample_json("change_request.json")
        payload = data.get(change_id, data["default"])
        payload["change_id"] = change_id
        return ChangeRequest.model_validate(payload)

    async def post_step_result(
        self,
        change_id: str,
        step_id: str,
        status: str,
        evidence_refs: list[dict] | None = None,
        notes: str | None = None,
    ) -> dict:
        _ = StepStatus(status)
        return {
            "ok": True,
            "change_id": change_id,
            "step_id": step_id,
            "status": status,
            "evidence_refs": evidence_refs or [],
            "notes": notes,
        }
