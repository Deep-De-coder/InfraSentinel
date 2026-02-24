import pytest

from services.mcp_netbox.handlers import NetboxHandlers


@pytest.mark.asyncio
async def test_get_expected_mapping() -> None:
    handlers = NetboxHandlers()
    out = await handlers.get_expected_mapping("CHG-001")
    assert "allowed_endpoints" in out
    assert out["allowed_endpoints"][0]["port_label"] == "24"


@pytest.mark.asyncio
async def test_validate_observed_match_and_mismatch() -> None:
    handlers = NetboxHandlers()
    ok = await handlers.validate_observed("CHG-001", "PANEL-A", "24", "MDF-01-R12-P24")
    bad = await handlers.validate_observed("CHG-001", "PANEL-A", "99", "MDF-01-R12-P24")
    assert ok.match is True
    assert bad.match is False
