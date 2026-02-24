import pytest

from services.mcp_cv.handlers import CVHandlers


@pytest.mark.asyncio
async def test_mock_port_label_deterministic() -> None:
    handlers = CVHandlers(cv_mode="mock")
    out = await handlers.read_port_label("evidence-good")
    assert out.port_label == "24"
    assert out.confidence >= 0.75


@pytest.mark.asyncio
async def test_low_confidence_has_retake_guidance() -> None:
    handlers = CVHandlers(cv_mode="mock")
    out = await handlers.read_port_label("evidence-low-confidence")
    assert out.confidence < 0.75
    assert len(out.retake_guidance) > 0
