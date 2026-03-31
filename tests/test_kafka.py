"""Kafka integration smoke tests.

These tests require a real Kafka broker. They are run in the kafka-smoke CI job
which starts a Kafka service container. Locally they skip automatically if
KAFKA_BOOTSTRAP_SERVERS does not point to a reachable broker.
"""

from __future__ import annotations

import os

import pytest

KAFKA_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


def _kafka_available() -> bool:
    """Attempt a lightweight probe to see if Kafka is reachable."""
    try:
        import socket

        host, port_str = KAFKA_SERVERS.split(":", 1)
        with socket.create_connection((host, int(port_str)), timeout=3):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _kafka_available(),
    reason="Kafka not reachable — set KAFKA_BOOTSTRAP_SERVERS to a live broker",
)

pytest.importorskip("aiokafka", reason="aiokafka not installed")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kafka_event_bus_connect_succeeds() -> None:
    from packages.core.kafka import KafkaEventBus

    bus = KafkaEventBus(KAFKA_SERVERS)
    await bus.connect()
    assert bus.is_connected
    await bus.disconnect()
    assert not bus.is_connected


@pytest.mark.asyncio
async def test_kafka_publish_and_consume_roundtrip() -> None:
    """Publish a message and verify it can be consumed back."""
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer  # type: ignore[import-untyped]
    from packages.core.kafka import KafkaEventBus
    import json

    topic = "infrasentinel.change.started"
    group_id = "test-consumer-group"

    bus = KafkaEventBus(KAFKA_SERVERS)
    await bus.connect()

    payload = {"change_id": "SMOKE-001", "mop_id": "TEST", "technician_id": "ci"}
    await bus.publish(topic, payload)

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_SERVERS,
        group_id=group_id,
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
    )
    await consumer.start()
    try:
        received = []
        async for msg in consumer:
            data = json.loads(msg.value.decode("utf-8"))
            received.append(data)
            break
        assert len(received) == 1
        assert received[0]["change_id"] == "SMOKE-001"
    finally:
        await consumer.stop()

    await bus.disconnect()


@pytest.mark.asyncio
async def test_kafka_graceful_noop_when_unreachable() -> None:
    """Publishing to an unreachable broker must not raise."""
    from packages.core.kafka import KafkaEventBus

    # Intentionally wrong port — should fail gracefully
    bus = KafkaEventBus("localhost:19999")
    await bus.connect()
    assert not bus.is_connected
    await bus.publish("infrasentinel.change.started", {"key": "value"})
