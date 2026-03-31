"""Async Kafka event bus with graceful degradation.

Kafka is a side-channel audit/event stream only — Temporal remains the orchestrator.
All publish failures are logged and swallowed so Kafka outages never affect workflows.
aiokafka is an optional dependency; if not installed the bus silently no-ops.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

INFRASENTINEL_TOPICS = [
    "infrasentinel.change.started",
    "infrasentinel.step.completed",
    "infrasentinel.quality.failed",
    "infrasentinel.cmdb.mismatch",
    "infrasentinel.proofpack.ready",
]

_kafka_bus: KafkaEventBus | None = None


def get_kafka_bus() -> KafkaEventBus | None:
    return _kafka_bus


def set_kafka_bus(bus: KafkaEventBus) -> None:
    global _kafka_bus
    _kafka_bus = bus


class KafkaEventBus:
    """AsyncIO Kafka producer wrapper.

    Gracefully degrades when Kafka is unreachable or aiokafka is not installed.
    """

    def __init__(self, bootstrap_servers: str) -> None:
        self.bootstrap_servers = bootstrap_servers
        self._producer: Any = None
        self._connected = False

    async def connect(self) -> None:
        try:
            from aiokafka import AIOKafkaProducer  # type: ignore[import-untyped]

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
            await self._producer.start()
            self._connected = True
            logger.info("Kafka connected to %s", self.bootstrap_servers)
        except ImportError:
            logger.warning("aiokafka not installed; Kafka publishing disabled")
        except Exception as exc:
            logger.warning("Kafka connection failed (%s); publishing disabled", exc)

    async def disconnect(self) -> None:
        if self._producer is not None and self._connected:
            try:
                await self._producer.stop()
            except Exception as exc:
                logger.warning("Kafka disconnect error: %s", exc)
        self._connected = False
        self._producer = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def publish(self, topic: str, event: dict) -> None:
        """Publish event dict to a Kafka topic.  Never raises — failures are logged."""
        if not self._connected or self._producer is None:
            return
        try:
            await self._producer.send_and_wait(topic, value=event)
        except Exception as exc:
            logger.warning("Kafka publish failed for topic %s: %s", topic, exc)
