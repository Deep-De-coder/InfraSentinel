from __future__ import annotations

from services.common import setup_stderr_logging
from services.mcp_ticketing.handlers import TicketingHandlers

logger = setup_stderr_logging("mcp_ticketing")
handlers = TicketingHandlers()


def build_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("ticketing")

    @server.tool(name="ticketing.get_change")
    async def get_change(change_id: str):
        logger.info("ticketing.get_change called")
        return (await handlers.get_change(change_id=change_id)).model_dump(mode="json")

    @server.tool(name="ticketing.post_step_result")
    async def post_step_result(
        change_id: str,
        step_id: str,
        status: str,
        evidence_refs: list[dict] | None = None,
        notes: str | None = None,
    ):
        logger.info("ticketing.post_step_result called")
        return await handlers.post_step_result(
            change_id=change_id,
            step_id=step_id,
            status=status,
            evidence_refs=evidence_refs,
            notes=notes,
        )

    return server


if __name__ == "__main__":
    build_server().run()
