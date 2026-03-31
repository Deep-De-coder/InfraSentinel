"""E2E API tests with mocked Temporal client.

Tests the FastAPI layer end-to-end without a running Temporal server.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytest.importorskip("temporalio", reason="temporalio not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from httpx import AsyncClient, ASGITransport  # noqa: E402

from apps.api.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_temporal_client() -> MagicMock:
    client = MagicMock()
    handle = MagicMock()
    handle.result_run_id = "run-abc-123"
    client.start_workflow = AsyncMock(return_value=handle)
    client.get_workflow_handle = MagicMock(return_value=handle)
    handle.signal = AsyncMock(return_value=None)
    handle.query = AsyncMock(return_value={})
    return client


@pytest.fixture
def mock_kafka_bus() -> MagicMock:
    bus = MagicMock()
    bus.is_connected = False
    bus.connect = AsyncMock()
    bus.disconnect = AsyncMock()
    bus.publish = AsyncMock()
    return bus


# ---------------------------------------------------------------------------
# POST /v1/changes/start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_change_returns_workflow_id(
    mock_temporal_client: MagicMock, mock_kafka_bus: MagicMock
) -> None:
    with (
        patch("apps.api.deps.get_temporal_client", AsyncMock(return_value=mock_temporal_client)),
        patch("packages.core.kafka.KafkaEventBus", return_value=mock_kafka_bus),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/changes/start",
                json={"change_id": "CHG-E2E-001", "scenario": "CHG-001_A"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow_id"] == "change-CHG-E2E-001"
    assert "run_id" in data


@pytest.mark.asyncio
async def test_start_change_conflict_returns_409(
    mock_kafka_bus: MagicMock,
) -> None:
    from temporalio.exceptions import WorkflowAlreadyStartedError

    conflict_client = MagicMock()
    conflict_client.start_workflow = AsyncMock(
        side_effect=WorkflowAlreadyStartedError("change-CHG-E2E-001", "", "")
    )

    with (
        patch("apps.api.deps.get_temporal_client", AsyncMock(return_value=conflict_client)),
        patch("packages.core.kafka.KafkaEventBus", return_value=mock_kafka_bus),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/changes/start",
                json={"change_id": "CHG-E2E-001", "scenario": "CHG-001_A"},
            )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /v1/evidence/upload — fixture IDs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_evidence_quality_pass(
    mock_temporal_client: MagicMock, mock_kafka_bus: MagicMock
) -> None:
    """CHG-001_A happy-path fixture should pass quality gate and be accepted."""
    with (
        patch("apps.api.deps.get_temporal_client", AsyncMock(return_value=mock_temporal_client)),
        patch("packages.core.kafka.KafkaEventBus", return_value=mock_kafka_bus),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/evidence/upload",
                data={
                    "change_id": "CHG-001",
                    "step_id": "step-cable-check",
                    "evidence_id": "ev-001",
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["evidence_id"] == "ev-001"
    assert data["status"] in ("verifying", "needs_retake")


@pytest.mark.asyncio
async def test_upload_evidence_quality_failure(
    mock_temporal_client: MagicMock, mock_kafka_bus: MagicMock
) -> None:
    """CHG-001_C fixture is designed to fail the quality gate."""
    with (
        patch("apps.api.deps.get_temporal_client", AsyncMock(return_value=mock_temporal_client)),
        patch("packages.core.kafka.KafkaEventBus", return_value=mock_kafka_bus),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/evidence/upload",
                data={
                    "change_id": "CHG-001",
                    "step_id": "step-cable-check",
                    "evidence_id": "ev-blurry",
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert "evidence_id" in data


# ---------------------------------------------------------------------------
# GET /v1/changes/{id}/proofpack
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_proofpack_not_found(mock_kafka_bus: MagicMock) -> None:
    with patch("packages.core.kafka.KafkaEventBus", return_value=mock_kafka_bus):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/v1/changes/CHG-NONEXISTENT/proofpack")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /healthz
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthz_returns_ok(mock_kafka_bus: MagicMock) -> None:
    with patch("packages.core.kafka.KafkaEventBus", return_value=mock_kafka_bus):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/healthz")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "otlp_configured" in data
    assert "langfuse_configured" in data
    assert "kafka_connected" in data
