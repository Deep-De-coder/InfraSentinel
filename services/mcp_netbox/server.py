from __future__ import annotations

from services.common import setup_stderr_logging
from services.mcp_netbox.handlers import NetboxHandlers

logger = setup_stderr_logging("mcp_netbox")
handlers = NetboxHandlers()


def build_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("netbox")

    @server.tool(name="netbox.get_expected_mapping")
    async def get_expected_mapping(change_id: str):
        logger.info("netbox.get_expected_mapping called")
        return (await handlers.get_expected_mapping(change_id=change_id)).model_dump(mode="json")

    @server.tool(name="netbox.validate_observed")
    async def validate_observed(change_id: str, panel_id: str, port_label: str, cable_tag: str):
        logger.info("netbox.validate_observed called")
        return (
            await handlers.validate_observed(
                change_id=change_id,
                panel_id=panel_id,
                port_label=port_label,
                cable_tag=cable_tag,
            )
        ).model_dump(mode="json")

    return server


if __name__ == "__main__":
    build_server().run()
