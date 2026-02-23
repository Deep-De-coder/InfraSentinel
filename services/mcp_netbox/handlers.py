from __future__ import annotations

from packages.core.models import ExpectedMapping, ValidationResult
from services.common import load_sample_json


class NetboxHandlers:
    async def get_expected_mapping(self, change_id: str) -> ExpectedMapping:
        data = load_sample_json("netbox_expected_mapping.json")
        mapping = data.get(change_id, data["default"])
        return ExpectedMapping(
            change_id=change_id,
            panel_id=mapping["panel_id"],
            port_label=mapping["port_label"],
            cable_tag=mapping["cable_tag"],
        )

    async def validate_observed(
        self, change_id: str, panel_id: str, port_label: str, cable_tag: str
    ) -> ValidationResult:
        expected = await self.get_expected_mapping(change_id=change_id)
        match = (
            expected.panel_id == panel_id
            and expected.port_label == port_label
            and expected.cable_tag == cable_tag
        )
        if match:
            return ValidationResult(match=True, reason="Observed mapping matches NetBox.", confidence=0.99)
        return ValidationResult(
            match=False,
            reason=(
                f"Expected ({expected.panel_id}, {expected.port_label}, {expected.cable_tag}) "
                f"but got ({panel_id}, {port_label}, {cable_tag})"
            ),
            confidence=0.99,
        )
