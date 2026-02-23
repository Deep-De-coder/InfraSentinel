from __future__ import annotations

from services.common import setup_stderr_logging
from services.mcp_cv.handlers import CVHandlers

logger = setup_stderr_logging("mcp_cv")
handlers = CVHandlers()


def build_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("cv")

    @server.tool(name="cv.read_port_label")
    async def read_port_label(evidence_id: str):
        logger.info("cv.read_port_label called")
        return (await handlers.read_port_label(evidence_id=evidence_id)).model_dump(mode="json")

    @server.tool(name="cv.read_cable_tag")
    async def read_cable_tag(evidence_id: str):
        logger.info("cv.read_cable_tag called")
        return (await handlers.read_cable_tag(evidence_id=evidence_id)).model_dump(mode="json")

    return server


if __name__ == "__main__":
    build_server().run()
