"""Kafka consumer that turns platform events into analytics data and metrics."""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from datetime import datetime, timezone
from typing import Any

from kafka import KafkaConsumer
from prometheus_client import Counter, Gauge, start_http_server
from psycopg2.extras import Json

try:
    from src.utils.connections import conn_env
except ImportError:
    from utils.connections import conn_env


LOGGER = logging.getLogger(__name__)

DEFAULT_TOPICS = ("weather_snapshots", "itinerary_requests")

CONSUMED_EVENTS_TOTAL = Counter(
    "holiday_kafka_consumed_events_total",
    "Kafka analytics events consumed by topic and event type.",
    ["topic", "event_type"],
)
CONSUMER_ERRORS_TOTAL = Counter(
    "holiday_kafka_consumer_errors_total",
    "Kafka analytics consumer errors.",
    ["stage"],
)
LATEST_EVENT_TIMESTAMP_SECONDS = Gauge(
    "holiday_kafka_latest_event_timestamp_seconds",
    "Unix timestamp of the latest consumed Kafka event by topic.",
    ["topic"],
)
ITINERARY_EVENTS_TOTAL = Counter(
    "holiday_analytics_itinerary_events_total",
    "Consumed itinerary events by city.",
    ["city"],
)
WEATHER_EVENTS_TOTAL = Counter(
    "holiday_analytics_weather_events_total",
    "Consumed weather events by city.",
    ["city"],
)
ITINERARY_CATEGORY_MATCH_RATE = Gauge(
    "holiday_analytics_itinerary_category_match_rate",
    "Latest consumed itinerary category match rate by city.",
    ["city"],
)
ITINERARY_WEATHER_SUITABILITY_SCORE = Gauge(
    "holiday_analytics_itinerary_weather_suitability_score",
    "Latest consumed itinerary weather suitability score by city.",
    ["city"],
)
WEATHER_TEMPERATURE_CELSIUS = Gauge(
    "holiday_analytics_weather_temperature_celsius",
    "Latest consumed weather temperature by city.",
    ["city"],
)


def _parse_event_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_timestamp_seconds(value: Any) -> float:
    parsed = _parse_event_time(value)
    if parsed is None:
        return time.time()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _create_tables() -> None:
    with conn_env() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_kafka_events (
                    id BIGSERIAL PRIMARY KEY,
                    topic TEXT NOT NULL,
                    partition INT NOT NULL,
                    offset_value BIGINT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_time TIMESTAMPTZ,
                    city TEXT,
                    categories JSONB,
                    selected_place_count INT,
                    category_match_rate DOUBLE PRECISION,
                    avg_distance_km DOUBLE PRECISION,
                    avg_recommendations DOUBLE PRECISION,
                    weather_suitability_score DOUBLE PRECISION,
                    temperature_2m DOUBLE PRECISION,
                    rain DOUBLE PRECISION,
                    wind_speed_10m DOUBLE PRECISION,
                    payload JSONB NOT NULL,
                    consumed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (topic, partition, offset_value)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analytics_kafka_events_topic_time
                ON analytics_kafka_events (topic, event_time DESC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analytics_kafka_events_city_time
                ON analytics_kafka_events (city, event_time DESC)
                """
            )


def _insert_event(topic: str, partition: int, offset: int, event: dict[str, Any]) -> bool:
    payload = event.get("payload") or {}
    quality_metrics = payload.get("quality_metrics") or {}
    weather = payload.get("weather") or {}
    event_type = str(event.get("event_type") or "unknown")
    event_time = _parse_event_time(event.get("event_time"))
    city = payload.get("city")
    categories = payload.get("categories")

    with conn_env() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analytics_kafka_events (
                    topic,
                    partition,
                    offset_value,
                    event_type,
                    event_time,
                    city,
                    categories,
                    selected_place_count,
                    category_match_rate,
                    avg_distance_km,
                    avg_recommendations,
                    weather_suitability_score,
                    temperature_2m,
                    rain,
                    wind_speed_10m,
                    payload
                )
                VALUES (
                    %(topic)s,
                    %(partition)s,
                    %(offset)s,
                    %(event_type)s,
                    %(event_time)s,
                    %(city)s,
                    %(categories)s,
                    %(selected_place_count)s,
                    %(category_match_rate)s,
                    %(avg_distance_km)s,
                    %(avg_recommendations)s,
                    %(weather_suitability_score)s,
                    %(temperature_2m)s,
                    %(rain)s,
                    %(wind_speed_10m)s,
                    %(payload)s
                )
                ON CONFLICT (topic, partition, offset_value) DO NOTHING
                RETURNING id
                """,
                {
                    "topic": topic,
                    "partition": partition,
                    "offset": offset,
                    "event_type": event_type,
                    "event_time": event_time,
                    "city": city,
                    "categories": Json(categories) if categories is not None else None,
                    "selected_place_count": payload.get("selected_place_count"),
                    "category_match_rate": _number(
                        quality_metrics.get("category_match_rate")
                    ),
                    "avg_distance_km": _number(quality_metrics.get("avg_distance_km")),
                    "avg_recommendations": _number(
                        quality_metrics.get("avg_recommendations")
                    ),
                    "weather_suitability_score": _number(
                        quality_metrics.get("weather_suitability_score")
                    ),
                    "temperature_2m": _number(weather.get("temperature_2m")),
                    "rain": _number(weather.get("rain")),
                    "wind_speed_10m": _number(weather.get("wind_speed_10m")),
                    "payload": Json(payload),
                },
            )
            return cursor.fetchone() is not None


def _record_metrics(topic: str, event: dict[str, Any]) -> None:
    payload = event.get("payload") or {}
    event_type = str(event.get("event_type") or "unknown")
    city = str(payload.get("city") or "unknown")
    CONSUMED_EVENTS_TOTAL.labels(topic, event_type).inc()
    LATEST_EVENT_TIMESTAMP_SECONDS.labels(topic).set(
        _event_timestamp_seconds(event.get("event_time"))
    )

    if topic == "itinerary_requests":
        quality_metrics = payload.get("quality_metrics") or {}
        ITINERARY_EVENTS_TOTAL.labels(city).inc()
        category_match_rate = _number(quality_metrics.get("category_match_rate"))
        weather_suitability = _number(
            quality_metrics.get("weather_suitability_score")
        )
        if category_match_rate is not None:
            ITINERARY_CATEGORY_MATCH_RATE.labels(city).set(category_match_rate)
        if weather_suitability is not None:
            ITINERARY_WEATHER_SUITABILITY_SCORE.labels(city).set(weather_suitability)

    if topic == "weather_snapshots":
        weather = payload.get("weather") or {}
        WEATHER_EVENTS_TOTAL.labels(city).inc()
        temperature = _number(weather.get("temperature_2m"))
        if temperature is not None:
            WEATHER_TEMPERATURE_CELSIUS.labels(city).set(temperature)


def _consumer() -> KafkaConsumer:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092").split(",")
    topics = tuple(
        topic.strip()
        for topic in os.getenv("KAFKA_ANALYTICS_TOPICS", ",".join(DEFAULT_TOPICS)).split(
            ","
        )
        if topic.strip()
    )
    return KafkaConsumer(
        *topics,
        bootstrap_servers=bootstrap_servers,
        group_id=os.getenv("KAFKA_ANALYTICS_GROUP_ID", "holiday-analytics-consumer"),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        auto_offset_reset=os.getenv("KAFKA_ANALYTICS_OFFSET_RESET", "earliest"),
        enable_auto_commit=False,
        consumer_timeout_ms=1000,
    )


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    metrics_port = int(os.getenv("KAFKA_ANALYTICS_METRICS_PORT", "9108"))
    shutdown = False

    def handle_shutdown(_signum, _frame) -> None:
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    _create_tables()
    start_http_server(metrics_port)
    LOGGER.info("Kafka analytics consumer metrics listening on :%s", metrics_port)

    while not shutdown:
        consumer = None
        try:
            consumer = _consumer()
            LOGGER.info("Kafka analytics consumer started")
            while not shutdown:
                for message in consumer:
                    inserted = _insert_event(
                        message.topic,
                        message.partition,
                        message.offset,
                        message.value,
                    )
                    _record_metrics(message.topic, message.value)
                    consumer.commit()
                    LOGGER.info(
                        "Consumed topic=%s partition=%s offset=%s inserted=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                        inserted,
                    )
                    if shutdown:
                        break
        except Exception:
            CONSUMER_ERRORS_TOTAL.labels("consume").inc()
            LOGGER.exception("Kafka analytics consumer failed; retrying")
            time.sleep(5)
        finally:
            if consumer is not None:
                consumer.close()


if __name__ == "__main__":
    main()
