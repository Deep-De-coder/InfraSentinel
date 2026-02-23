from __future__ import annotations

from packages.core.config import Settings


class NetBoxAdapter:
    """Real NetBox adapter skeleton."""

    def __init__(self, settings: Settings):
        self.base_url = settings.netbox_url
        self.token = settings.netbox_token

    async def get_expected_mapping(self, change_id: str) -> dict:
        raise NotImplementedError("Implement NetBox API lookup here.")

    async def validate_observed(self, change_id: str, panel_id: str, port_label: str, cable_tag: str) -> dict:
        raise NotImplementedError("Implement NetBox API validation here.")
