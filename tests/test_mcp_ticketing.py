import pytest

from services.mcp_ticketing.handlers import TicketingHandlers


@pytest.mark.asyncio
async def test_get_change_and_post_result() -> None:
    handlers = TicketingHandlers()
    change = await handlers.get_change("CHG-001")
    assert change.change_id == "CHG-001"
    assert len(change.steps) >= 1

    out = await handlers.post_step_result("CHG-001", "S1", "VERIFIED")
    assert out["ok"] is True
