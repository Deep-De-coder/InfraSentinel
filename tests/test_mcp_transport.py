"""Tests for MCPToolRouter in-process transport and adapter wiring."""

from __future__ import annotations

import pytest

from packages.mcp.client import MCPToolRouter
from services.mcp_camera.adapter import CameraAdapter
from services.mcp_cv.adapter import CVAdapter
from services.mcp_netbox.adapter import NetBoxAdapter
from services.mcp_ticketing.adapter import TicketingAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_router() -> MCPToolRouter:
    return MCPToolRouter.from_adapters(
        camera_adapter=CameraAdapter(camera_mode="mock"),
        cv_adapter=CVAdapter(cv_mode="mock", scenario="CHG-001_A"),
        netbox_adapter=NetBoxAdapter(netbox_mode="mock"),
        ticketing_adapter=TicketingAdapter(ticketing_mode="mock"),
    )


# ---------------------------------------------------------------------------
# Router wiring
# ---------------------------------------------------------------------------


def test_router_from_adapters_has_all_slots() -> None:
    router = _make_router()
    assert callable(router.camera_capture_frame)
    assert callable(router.camera_store_evidence)
    assert callable(router.cv_read_port_label)
    assert callable(router.cv_read_cable_tag)
    assert callable(router.netbox_get_expected_mapping)
    assert callable(router.netbox_validate_observed)
    assert callable(router.ticketing_get_change)
    assert callable(router.ticketing_post_step_result)
    assert callable(router.ticketing_request_approval)


def test_router_from_settings_returns_router() -> None:
    """from_settings() must succeed in mock mode (no real services required)."""
    router = MCPToolRouter.from_settings()
    assert isinstance(router, MCPToolRouter)


# ---------------------------------------------------------------------------
# Mock mode fixture-shaped responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cv_read_port_label_mock_fixture_shape() -> None:
    router = _make_router()
    result = await router.read_port_label("ev-001", change_id="CHG-001", scenario="CHG-001_A")
    assert hasattr(result, "port_label")
    assert hasattr(result, "confidence")
    assert isinstance(result.confidence, float)


@pytest.mark.asyncio
async def test_cv_read_cable_tag_mock_fixture_shape() -> None:
    router = _make_router()
    result = await router.read_cable_tag("ev-001", change_id="CHG-001", scenario="CHG-001_A")
    assert hasattr(result, "cable_tag")
    assert hasattr(result, "confidence")


@pytest.mark.asyncio
async def test_netbox_get_expected_mapping_mock_shape() -> None:
    router = _make_router()
    result = await router.get_expected_mapping("CHG-001")
    assert isinstance(result, dict)
    assert "allowed_endpoints" in result or "default" in result


@pytest.mark.asyncio
async def test_netbox_validate_observed_mock_match() -> None:
    router = _make_router()
    result = await router.validate_observed("CHG-001", "PANEL-A", "24", "MDF-01-R12-P24")
    assert hasattr(result, "match")
    assert isinstance(result.match, bool)


@pytest.mark.asyncio
async def test_ticketing_get_change_mock_shape() -> None:
    router = _make_router()
    change = await router.get_change("CHG-001")
    assert change is not None


@pytest.mark.asyncio
async def test_ticketing_post_step_result_mock() -> None:
    router = _make_router()
    result = await router.post_step_result(
        change_id="CHG-001",
        step_id="step-1",
        status="verified",
        evidence_refs=[],
        notes="All good",
    )
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ---------------------------------------------------------------------------
# Missing handler raises a clear error (not KeyError)
# ---------------------------------------------------------------------------


def test_missing_handler_raises_attribute_error() -> None:
    """Accessing a non-existent tool slot raises AttributeError, not KeyError."""
    router = _make_router()
    with pytest.raises(AttributeError):
        _ = router.nonexistent_tool  # type: ignore[attr-defined]
