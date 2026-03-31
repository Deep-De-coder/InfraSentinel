"""NetBox adapter — switches between mock fixtures and real NetBox REST API."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PortInfo:
    port_id: str
    device: str
    port_label: str
    cable_id: str | None = None
    cable_label: str | None = None


class NetBoxAdapter:
    """Unified NetBox adapter.

    NETBOX_MODE=mock  → returns fixture data via NetboxHandlers
    NETBOX_MODE=netbox → calls real NetBox REST via netbox_client
    """

    def __init__(self, netbox_mode: str | None = None) -> None:
        self.netbox_mode = (netbox_mode or os.getenv("NETBOX_MODE", "mock")).lower()

    # --- high-level domain API ---

    async def get_port_info(self, port_id: str) -> PortInfo:
        """Return metadata for a single port by composite ID (panel_id:port_label)."""
        parts = port_id.split(":", 1)
        panel_id = parts[0]
        port_label = parts[1] if len(parts) > 1 else ""

        if self.netbox_mode == "netbox":
            from packages.core.config import get_settings
            from services.mcp_netbox.src.netbox_client import _get_device_id, _get_front_port_cable

            settings = get_settings()
            device_id = _get_device_id(settings.netbox_url, settings.netbox_token, panel_id)
            if device_id is None:
                return PortInfo(port_id=port_id, device=panel_id, port_label=port_label)
            cable_data = _get_front_port_cable(
                settings.netbox_url, settings.netbox_token, device_id, port_label
            )
            cable_label = cable_data.get("label") if cable_data else None
            cable_id = str(cable_data.get("id")) if cable_data else None
            return PortInfo(
                port_id=port_id,
                device=panel_id,
                port_label=port_label,
                cable_id=cable_id,
                cable_label=cable_label,
            )

        # mock mode — pull from fixture
        from packages.core.fixtures.loaders import load_expected_mapping

        change_id = panel_id
        mapping = load_expected_mapping(change_id)
        endpoints = mapping.get("allowed_endpoints", [])
        for ep in endpoints:
            if ep.get("panel_id") == panel_id and ep.get("port_label") == port_label:
                return PortInfo(
                    port_id=port_id,
                    device=panel_id,
                    port_label=port_label,
                    cable_label=ep.get("cable_tag"),
                )
        return PortInfo(port_id=port_id, device=panel_id, port_label=port_label)

    async def validate_cable(self, port_a: str, port_b: str) -> bool:
        """Return True if port_a and port_b belong to the same cable (by label)."""
        info_a = await self.get_port_info(port_a)
        info_b = await self.get_port_info(port_b)
        if not info_a.cable_label or not info_b.cable_label:
            return False
        return info_a.cable_label == info_b.cable_label

    # --- MCPToolRouter-compatible async methods ---

    async def get_expected_mapping(self, change_id: str) -> dict:
        from services.mcp_netbox.handlers import NetboxHandlers

        return await NetboxHandlers().get_expected_mapping(change_id)

    async def validate_observed(
        self, change_id: str, panel_id: str, port_label: str, cable_tag: str
    ) -> object:
        from services.mcp_netbox.handlers import NetboxHandlers

        return await NetboxHandlers().validate_observed(change_id, panel_id, port_label, cable_tag)
