import pytest

from services.mcp_cv.handlers import CVHandlers


@pytest.mark.asyncio
async def test_cv_read_port_label() -> None:
    handlers = CVHandlers()
    out = await handlers.read_port_label("evidence-good")
    assert out.panel_id == "PANEL-A"
    assert out.port_label == "A-24"
    assert out.confidence > 0.9


@pytest.mark.asyncio
async def test_cv_read_cable_tag() -> None:
    handlers = CVHandlers()
    out = await handlers.read_cable_tag("evidence-good")
    assert out.cable_tag == "CAB-9001"
