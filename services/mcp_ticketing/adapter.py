from __future__ import annotations


class TicketingAdapter:
    """Real ticketing adapter skeleton."""

    async def get_change(self, change_id: str) -> dict:
        raise NotImplementedError("Implement ticket system lookup.")

    async def post_step_result(self, change_id: str, step_id: str, status: str, notes: str | None = None) -> dict:
        raise NotImplementedError("Implement posting step results to ticket system.")
