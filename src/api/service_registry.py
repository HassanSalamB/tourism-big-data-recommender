"""Validated backend service links for the public portfolio."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Mapping, cast

BackendStatus = Literal["recorded", "live", "maintenance"]
VALID_BACKEND_STATUSES = {"recorded", "live", "maintenance"}
SERVICE_ENVIRONMENT_VARIABLES = {
    "streamlit": ("Streamlit", "SERVICE_STREAMLIT_URL"),
    "fastapi": ("FastAPI", "SERVICE_FASTAPI_URL"),
    "airflow": ("Airflow", "SERVICE_AIRFLOW_URL"),
    "kafka": ("Kafka UI", "SERVICE_KAFKA_UI_URL"),
    "spark": ("Spark", "SERVICE_SPARK_URL"),
    "grafana": ("Grafana", "SERVICE_GRAFANA_URL"),
    "prometheus": ("Prometheus", "SERVICE_PROMETHEUS_URL"),
    "neo4j": ("Neo4j", "SERVICE_NEO4J_URL"),
    "adminer": ("Adminer", "SERVICE_ADMINER_URL"),
}


@dataclass(frozen=True)
class ServiceEndpoint:
    name: str
    environment_variable: str
    url: str | None


def backend_status_message(status: BackendStatus) -> tuple[str, str, str]:
    """Return presentation-neutral copy for the current backend state."""
    messages = {
        "recorded": (
            "notice",
            "Recorded engineering evidence",
            "The public portfolio is live; backend panels show evidence from verified local executions.",
        ),
        "live": (
            "live-note",
            "Live engineering environment",
            "Configured service buttons open the Proxmox-backed platform.",
        ),
        "maintenance": (
            "notice",
            "Engineering environment in maintenance",
            "Recorded evidence remains available while the private lab is offline.",
        ),
    }
    return messages[status]


def load_backend_status(environ: Mapping[str, str] | None = None) -> BackendStatus:
    """Return a validated backend state, defaulting to recorded evidence."""
    source = os.environ if environ is None else environ
    value = source.get("BACKEND_ENVIRONMENT_STATUS", "recorded").strip().lower()
    if value not in VALID_BACKEND_STATUSES:
        raise ValueError(
            "BACKEND_ENVIRONMENT_STATUS must be recorded, live, or maintenance"
        )
    return cast(BackendStatus, value)


def load_service_registry(
    environ: Mapping[str, str] | None = None,
) -> dict[str, ServiceEndpoint]:
    """Load optional public URLs without requiring any service to be online."""
    source = os.environ if environ is None else environ
    return {
        key: ServiceEndpoint(
            name,
            variable,
            source.get(variable, "").strip().rstrip("/") or None,
        )
        for key, (name, variable) in SERVICE_ENVIRONMENT_VARIABLES.items()
    }


def service_call_to_action(
    status: BackendStatus, endpoint: ServiceEndpoint
) -> tuple[str, str] | None:
    """Return a live link only for verified live environments with a URL."""
    if status != "live" or endpoint.url is None:
        return None
    return f"Open live {endpoint.name}", endpoint.url
