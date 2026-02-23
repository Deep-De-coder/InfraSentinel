import pytest

from services.mcp_ticketing.handlers import TicketingHandlers


@pytest.mark.asyncio
async def test_get_change_and_post_result() -> None:
    handlers = TicketingHandlers()
    change = await handlers.get_change("CHG-1001")
    assert change.change_id == "CHG-1001"
    assert len(change.steps) >= 1

    out = await handlers.post_step_result("CHG-1001", "step-1", "VERIFIED")
    assert out["ok"] is True
