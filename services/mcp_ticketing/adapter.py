"""Ticketing adapter — mock writes to ticketing_log.json; real stub for ServiceNow/Jira."""

from __future__ import annotations

import os


class TicketingAdapter:
    """Unified ticketing adapter.

    TICKETING_MODE=mock → writes to runtime/ticketing_log.json via TicketingHandlers
    TICKETING_MODE=real → stub ready for ServiceNow/Jira wiring (see TODO below)
    """

    def __init__(self, ticketing_mode: str | None = None) -> None:
        self.ticketing_mode = (ticketing_mode or os.getenv("TICKETING_MODE", "mock")).lower()

    # --- high-level domain API ---

    async def create_ticket(self, change_id: str, summary: str) -> str:
        """Create a ticket for a change and return the ticket_id."""
        if self.ticketing_mode == "real":
            # TODO: wire to ServiceNow/Jira
            # Example: POST /api/now/table/incident with change_id + summary
            raise NotImplementedError("Real ticketing backend not yet wired.")

        from services.mcp_ticketing.handlers import TicketingHandlers

        handlers = TicketingHandlers()
        result = await handlers.post_step_result(
            change_id=change_id,
            step_id="ticket",
            status="open",
            notes=summary,
        )
        return f"TKT-{change_id}"

    async def update_ticket(self, ticket_id: str, status: str, notes: str) -> bool:
        """Update ticket status and add notes. Returns True on success."""
        if self.ticketing_mode == "real":
            # TODO: wire to ServiceNow/Jira
            # Example: PATCH /api/now/table/incident/{ticket_id}
            raise NotImplementedError("Real ticketing backend not yet wired.")

        from services.mcp_ticketing.handlers import TicketingHandlers

        handlers = TicketingHandlers()
        change_id = ticket_id.removeprefix("TKT-") if ticket_id.startswith("TKT-") else ticket_id
        await handlers.post_step_result(
            change_id=change_id,
            step_id="update",
            status=status,
            notes=notes,
        )
        return True

    # --- MCPToolRouter-compatible async methods ---

    async def get_change(self, change_id: str) -> object:
        from services.mcp_ticketing.handlers import TicketingHandlers

        return await TicketingHandlers().get_change(change_id)

    async def post_step_result(
        self,
        change_id: str,
        step_id: str,
        status: str,
        evidence_refs: list[dict] | None = None,
        notes: str | None = None,
    ) -> dict:
        from services.mcp_ticketing.handlers import TicketingHandlers

        return await TicketingHandlers().post_step_result(
            change_id=change_id,
            step_id=step_id,
            status=status,
            evidence_refs=evidence_refs,
            notes=notes,
        )

    async def request_approval(
        self,
        change_id: str,
        step_id: str,
        reason: str,
        evidence_ids: list[str] | None = None,
        escalation_text: str | None = None,
    ) -> dict:
        from services.mcp_ticketing.handlers import TicketingHandlers

        return await TicketingHandlers().request_approval(
            change_id=change_id,
            step_id=step_id,
            reason=reason,
            evidence_ids=evidence_ids,
            escalation_text=escalation_text,
        )
