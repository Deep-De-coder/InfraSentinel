"""Unit tests for Kafka event schemas and KafkaEventBus (no real Kafka required)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.events import (
    BaseEvent,
    ChangeStartedEvent,
    CMDBMismatchEvent,
    ProofPackReadyEvent,
    QualityFailedEvent,
    StepCompletedEvent,
)
from packages.core.kafka import KafkaEventBus, get_kafka_bus, set_kafka_bus, INFRASENTINEL_TOPICS


# ---------------------------------------------------------------------------
# Event model serialization / deserialization
# ---------------------------------------------------------------------------


def test_base_event_has_correlation_id_and_timestamp() -> None:
    ev = BaseEvent()
    assert ev.correlation_id
    assert isinstance(ev.timestamp, datetime)


def test_change_started_event_round_trip() -> None:
    ev = ChangeStartedEvent(change_id="CHG-001", mop_id="MOP-01", technician_id="t1")
    data = ev.model_dump(mode="json")
    restored = ChangeStartedEvent.model_validate(data)
    assert restored.change_id == "CHG-001"
    assert restored.mop_id == "MOP-01"
    assert restored.technician_id == "t1"
    assert restored.correlation_id == ev.correlation_id


def test_step_completed_event_round_trip() -> None:
    ev = StepCompletedEvent(
        change_id="CHG-001", step_id="step-1", status="VERIFIED", ocr_text="24"
    )
    data = ev.model_dump(mode="json")
    restored = StepCompletedEvent.model_validate(data)
    assert restored.status == "VERIFIED"
    assert restored.ocr_text == "24"


def test_quality_failed_event_round_trip() -> None:
    metrics = {"blur_score": 50.0, "brightness": 40.0}
    ev = QualityFailedEvent(
        change_id="CHG-001",
        step_id="step-1",
        reason="Image too blurry",
        metrics=metrics,
    )
    data = ev.model_dump(mode="json")
    restored = QualityFailedEvent.model_validate(data)
    assert restored.reason == "Image too blurry"
    assert restored.metrics["blur_score"] == 50.0


def test_cmdb_mismatch_event_round_trip() -> None:
    ev = CMDBMismatchEvent(
        change_id="CHG-001",
        step_id="step-1",
        expected="PANEL-A:24:MDF-01-R12-P24",
        actual="PANEL-A:25:MDF-01-R12-P25",
    )
    data = ev.model_dump(mode="json")
    restored = CMDBMismatchEvent.model_validate(data)
    assert restored.expected != restored.actual


def test_proofpack_ready_event_round_trip() -> None:
    ev = ProofPackReadyEvent(
        change_id="CHG-001",
        proof_pack_url="runtime/proofpacks/CHG-001.json",
    )
    data = ev.model_dump(mode="json")
    restored = ProofPackReadyEvent.model_validate(data)
    assert restored.proof_pack_url == "runtime/proofpacks/CHG-001.json"


def test_event_timestamp_is_utc() -> None:
    ev = ChangeStartedEvent(change_id="CHG-001", mop_id="MOP-01", technician_id="t1")
    assert ev.timestamp.tzinfo is not None


def test_events_have_unique_correlation_ids() -> None:
    ev1 = BaseEvent()
    ev2 = BaseEvent()
    assert ev1.correlation_id != ev2.correlation_id


# ---------------------------------------------------------------------------
# KafkaEventBus — mocked aiokafka producer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_calls_send_and_wait_with_correct_topic() -> None:
    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock()
    mock_producer.send_and_wait = AsyncMock()

    with patch("aiokafka.AIOKafkaProducer", return_value=mock_producer):
        bus = KafkaEventBus("localhost:9092")
        await bus.connect()
        assert bus.is_connected

        event = {"change_id": "CHG-001", "status": "ok"}
        await bus.publish("infrasentinel.change.started", event)

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        assert call_args[0][0] == "infrasentinel.change.started"


@pytest.mark.asyncio
async def test_publish_is_noop_when_not_connected() -> None:
    """publish() must not raise when Kafka is unreachable (not connected)."""
    bus = KafkaEventBus("localhost:9092")
    # Don't call connect() — bus stays disconnected
    await bus.publish("infrasentinel.change.started", {"key": "value"})


@pytest.mark.asyncio
async def test_connect_gracefully_handles_import_error() -> None:
    """If aiokafka is not installed, connect() logs a warning and stays disconnected."""
    with patch.dict("sys.modules", {"aiokafka": None}):
        bus = KafkaEventBus("localhost:9092")
        await bus.connect()
        assert not bus.is_connected


@pytest.mark.asyncio
async def test_connect_gracefully_handles_connection_error() -> None:
    """If Kafka server is unreachable, connect() logs a warning and stays disconnected."""
    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock(side_effect=Exception("Connection refused"))

    with patch("aiokafka.AIOKafkaProducer", return_value=mock_producer):
        bus = KafkaEventBus("localhost:9092")
        await bus.connect()
        assert not bus.is_connected


@pytest.mark.asyncio
async def test_publish_failure_does_not_raise() -> None:
    """send_and_wait raising should be swallowed by publish()."""
    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock()
    mock_producer.send_and_wait = AsyncMock(side_effect=Exception("Broker unavailable"))

    with patch("aiokafka.AIOKafkaProducer", return_value=mock_producer):
        bus = KafkaEventBus("localhost:9092")
        await bus.connect()
        # This must not raise even though send_and_wait fails
        await bus.publish("infrasentinel.change.started", {"key": "value"})


@pytest.mark.asyncio
async def test_disconnect_stops_producer() -> None:
    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock()
    mock_producer.stop = AsyncMock()

    with patch("aiokafka.AIOKafkaProducer", return_value=mock_producer):
        bus = KafkaEventBus("localhost:9092")
        await bus.connect()
        await bus.disconnect()

    mock_producer.stop.assert_called_once()
    assert not bus.is_connected


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


def test_set_and_get_kafka_bus() -> None:
    bus = KafkaEventBus("localhost:9092")
    set_kafka_bus(bus)
    assert get_kafka_bus() is bus


# ---------------------------------------------------------------------------
# INFRASENTINEL_TOPICS list
# ---------------------------------------------------------------------------


def test_infrasentinel_topics_contains_all_five() -> None:
    expected = {
        "infrasentinel.change.started",
        "infrasentinel.step.completed",
        "infrasentinel.quality.failed",
        "infrasentinel.cmdb.mismatch",
        "infrasentinel.proofpack.ready",
    }
    assert expected == set(INFRASENTINEL_TOPICS)
