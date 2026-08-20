"""Kafka event publisher for product and data-platform events."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from kafka import KafkaProducer


DEFAULT_BOOTSTRAP_SERVERS = "kafka:9092"


@lru_cache(maxsize=1)
def _producer() -> KafkaProducer:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", DEFAULT_BOOTSTRAP_SERVERS)
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8") if value else None,
        linger_ms=20,
        retries=3,
    )


def publish_event(
    topic: str,
    event_type: str,
    payload: dict[str, Any],
    key: str | None = None,
) -> None:
    event = {
        "event_type": event_type,
        "event_time": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    future = _producer().send(topic, key=key, value=event)
    future.get(timeout=5)
