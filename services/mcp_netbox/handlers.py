"""NetBox MCP handlers with mock and real NetBox support."""

from __future__ import annotations

from packages.core.config import get_settings
from packages.core.fixtures.loaders import load_expected_mapping
from packages.core.models.legacy import ValidationResult

from services.mcp_netbox.src.netbox_client import (
    get_expected_mapping_netbox,
    validate_observed_netbox,
)


class NetboxHandlers:
    async def get_expected_mapping(self, change_id: str) -> dict:
        settings = get_settings()
        if settings.netbox_mode == "netbox":
            return get_expected_mapping_netbox(
                change_id, settings.netbox_url, settings.netbox_token
            )
        return load_expected_mapping(change_id)

    async def validate_observed(
        self, change_id: str, panel_id: str, port_label: str, cable_tag: str
    ) -> ValidationResult:
        settings = get_settings()
        if settings.netbox_mode == "netbox":
            return validate_observed_netbox(
                change_id,
                panel_id,
                port_label,
                cable_tag,
                settings.netbox_url,
                settings.netbox_token,
            )
        data = load_expected_mapping(change_id)
        allowed = data.get("allowed_endpoints", [])
        if not allowed:
            exp = data.get("default", data)
            if isinstance(exp, dict) and "panel_id" in exp:
                match = (
                    exp.get("panel_id") == panel_id
                    and exp.get("port_label") == port_label
                    and exp.get("cable_tag") == cable_tag
                )
                if match:
                    return ValidationResult(match=True, reason="Observed matches expected.", confidence=0.99)
                return ValidationResult(
                    match=False,
                    reason=f"Expected ({exp.get('panel_id')}, {exp.get('port_label')}, {exp.get('cable_tag')}) "
                    f"but got ({panel_id}, {port_label}, {cable_tag})",
                    confidence=0.99,
                )
        for ep in allowed:
            ep_panel = ep.get("panel_id")
            ep_port = ep.get("port_label") or ep.get("port_label_alt")
            ep_tag = ep.get("cable_tag")
            if ep_panel == panel_id and ep_port == port_label and ep_tag == cable_tag:
                return ValidationResult(match=True, reason="Observed matches allowed endpoint.", confidence=0.99)
        return ValidationResult(
            match=False,
            reason=f"No allowed endpoint matches ({panel_id}, {port_label}, {cable_tag})",
            confidence=0.99,
        )
