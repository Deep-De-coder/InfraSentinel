from __future__ import annotations

from services.common import setup_stderr_logging
from services.mcp_camera.handlers import CameraHandlers

logger = setup_stderr_logging("mcp_camera")
handlers = CameraHandlers()


def build_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("camera")

    @server.tool(name="camera.capture_frame")
    async def capture_frame(source: str):
        logger.info("camera.capture_frame called")
        return (await handlers.capture_frame(source=source)).model_dump(mode="json")

    @server.tool(name="camera.store_evidence")
    async def store_evidence(path: str | None = None, data_b64: str | None = None, metadata: dict | None = None):
        logger.info("camera.store_evidence called")
        return (
            await handlers.store_evidence(path=path, data_b64=data_b64, metadata=metadata or {})
        ).model_dump(mode="json")

    return server


if __name__ == "__main__":
    build_server().run()
