"""Ticketing MCP handlers with fixture support."""

from __future__ import annotations

import json
from pathlib import Path

from packages.core.fixtures.loaders import load_change
from packages.core.models.change import ChangeRequest
from packages.core.models.legacy import StepStatusLegacy


def _runtime_log_path() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime" / "ticketing_log.json"


def _append_log(entry: dict) -> None:
    p = _runtime_log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if p.exists():
        entries = json.loads(p.read_text(encoding="utf-8"))
    entries.append(entry)
    p.write_text(json.dumps(entries, indent=2), encoding="utf-8")


class TicketingHandlers:
    async def get_change(self, change_id: str) -> ChangeRequest:
        return load_change(change_id)

    async def post_step_result(
        self,
        change_id: str,
        step_id: str,
        status: str,
        evidence_refs: list[dict] | None = None,
        notes: str | None = None,
    ) -> dict:
        _ = StepStatusLegacy(status)
        entry = {
            "change_id": change_id,
            "step_id": step_id,
            "status": status,
            "evidence_refs": evidence_refs or [],
            "notes": notes,
        }
        _append_log(entry)
        return {"ok": True, **entry}

    async def request_approval(
        self,
        change_id: str,
        step_id: str,
        reason: str,
        evidence_ids: list[str] | None = None,
    ) -> dict:
        approval_id = f"APR-{change_id}-{step_id}"
        entry = {
            "type": "approval_request",
            "approval_request_id": approval_id,
            "change_id": change_id,
            "step_id": step_id,
            "reason": reason,
            "evidence_ids": evidence_ids or [],
        }
        _append_log(entry)
        return {"approval_request_id": approval_id, "ok": True}
