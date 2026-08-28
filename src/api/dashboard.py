"""Public portfolio and Streamlit UI for the Holiday Itinerary Data Platform."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

try:
    from src.api.dashboard_demo import WEATHER, demo_categories, demo_cities, demo_itinerary, demo_places, demo_summary
except ImportError:
    from dashboard_demo import WEATHER, demo_categories, demo_cities, demo_itinerary, demo_places, demo_summary

try:
    from src.api.service_registry import (
        backend_status_message,
        load_backend_status,
        load_service_registry,
        service_call_to_action,
    )
except ImportError:
    from service_registry import (
        backend_status_message,
        load_backend_status,
        load_service_registry,
        service_call_to_action,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = PROJECT_ROOT / "artifacts" / "screenshots"
ARCHITECTURE_HERO = PROJECT_ROOT / "docs" / "assets" / "holiday-platform-architecture.png"
LEVELS_OVERVIEW = PROJECT_ROOT / "docs" / "assets" / "holiday-platform-three-levels.png"
REPOSITORY_URL = "https://github.com/HassanSalamB/tourism-big-data-recommender"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PORTFOLIO_DEMO_MODE = os.getenv("PORTFOLIO_DEMO_MODE", "false").lower() in {"1", "true", "yes"}
BACKEND_STATUS = load_backend_status()
SERVICE_REGISTRY = load_service_registry()


st.set_page_config(page_title="Holiday Itinerary Data Platform", page_icon="🧭", layout="wide")
st.markdown(
    """
    <style>
      .block-container {max-width: 1240px; padding-top: 1.4rem; padding-bottom: 3rem;}
      [data-testid="stSidebar"] {border-right: 1px solid #e1e8e6;}
      [data-testid="stMetric"] {border: 1px solid #dce5e3; border-radius: 12px; padding: 12px 16px; background: #fff;}
      .hero {padding: 34px 38px; border-radius: 22px; color: #effaf7; background: linear-gradient(135deg,#071923,#0b3b3a); margin:.4rem 0 1.25rem;}
      .hero small {color:#67d4b8; font-weight:700; letter-spacing:.16em;}
      .hero h2 {color:#fff; font-size:2.25rem; margin:.5rem 0 .7rem; max-width:850px;}
      .hero p {color:#c5d8d5; font-size:1.04rem; max-width:850px; margin:0;}
      .card {min-height:145px; padding:20px; border:1px solid #dce6e3; border-radius:16px; background:#f8fbfa;}
      .card h3 {font-size:1.08rem; color:#123d3a; margin:0 0 .5rem;}
      .card p {font-size:.92rem; color:#536765; margin:0;}
      .notice {padding:13px 17px; border-radius:12px; background:#fff7e5; border:1px solid #ead49c; margin:.5rem 0 1rem;}
      .live-note {padding:13px 17px; border-radius:12px; background:#eaf7f3; border:1px solid #aed9cd; margin:.5rem 0 1rem;}
      .place-panel {border:1px solid #d8e1df; border-radius:10px; padding:.8rem 1rem; margin-bottom:.75rem; background:#fff;}
      .muted {color:#667875; font-size:.9rem;}
      .flow {padding:18px; border-radius:15px; background:#0b222b; color:#eaf5f2; line-height:2; text-align:center; margin:1rem 0;}
      .flow strong {color:#69d5b9;}
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str, **params) -> Any:
    response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any]) -> Any:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def platform_data() -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    if PORTFOLIO_DEMO_MODE:
        return demo_summary(), demo_cities(), demo_categories()
    return api_get("/summary"), api_get("/cities", limit=100), api_get("/categories", limit=300)


def mode_notice() -> None:
    if PORTFOLIO_DEMO_MODE:
        st.markdown(
            '<div class="notice"><strong>Public portfolio mode.</strong> The interface uses a small curated dataset so the original Streamlit experience remains interactive on Render. The complete DATAtourisme pipeline and backend services are demonstrated with real execution evidence throughout the system pages.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="live-note"><strong>Full-stack mode.</strong> Connected to the FastAPI service at <code>{API_BASE_URL}</code>.</div>',
            unsafe_allow_html=True,
        )


def backend_status_notice() -> None:
    css_class, heading, message = backend_status_message(BACKEND_STATUS)
    st.markdown(
        f'<div class="{css_class}"><strong>{heading}.</strong> {message}</div>',
        unsafe_allow_html=True,
    )


def home_page() -> None:
    st.title("Holiday Itinerary Data Platform")
    st.caption("An end-to-end data engineering portfolio project built around French tourism data")
    st.markdown(
        """
        <div class="hero">
          <small>DATA ENGINEERING · ANALYTICS · PLATFORM OPERATIONS</small>
          <h2>From raw tourism feeds to explainable, observable itinerary products</h2>
          <p>The platform ingests DATAtourisme data, preserves change history, builds trusted relational and graph models,
          serves itinerary APIs, emits operational events, and exposes the system through monitoring dashboards.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.image(str(ARCHITECTURE_HERO), width="stretch")
    st.caption("The complete platform at a glance—from DATAtourisme ingestion to the itinerary UI and operational telemetry.")

    st.subheader("Explore the live product and recorded engineering evidence")
    st.metric("Backend environment", BACKEND_STATUS.title())
    cols = st.columns(4)
    with cols[0]:
        st.image(str(SCREENSHOTS / "01-streamlit-dashboard.png"), width="stretch")
        st.page_link(APP_PAGE, label="Itinerary App", icon="🧭")
    with cols[1]:
        st.image(str(SCREENSHOTS / "03-airflow-dag-grid.png"), width="stretch")
        st.page_link(PIPELINE_PAGE, label="Pipeline & Storage", icon="🔄")
    with cols[2]:
        st.image(str(SCREENSHOTS / "02-fastapi-docs.png"), width="stretch")
        st.page_link(SERVING_PAGE, label="Serving & Graph", icon="🔌")
    with cols[3]:
        st.image(str(SCREENSHOTS / "11-grafana-kpis.png"), width="stretch")
        st.page_link(OBSERVABILITY_PAGE, label="Observability", icon="📊")

    st.subheader("Three levels of the system")
    st.image(str(LEVELS_OVERVIEW), width="stretch")
    st.caption("Serving, incremental ETL, and observability are separated so each layer can evolve and fail independently.")

    st.subheader("What this repository demonstrates")
    capabilities = st.columns(4)
    capabilities[0].metric("Data layers", "Bronze → Gold")
    capabilities[1].metric("Storage models", "SQL + Graph")
    capabilities[2].metric("Delivery", "API + Streamlit")
    capabilities[3].metric("Operations", "Metrics + Alerts")


def itinerary_page() -> None:
    st.title("Holiday Itinerary Dashboard")
    st.caption("The original Streamlit product experience")
    mode_notice()
    try:
        summary, cities, categories = platform_data()
    except requests.RequestException as exc:
        st.error(f"FastAPI is not reachable at {API_BASE_URL}.")
        st.exception(exc)
        st.stop()

    metric_cols = st.columns(5)
    metric_cols[0].metric("Places", f"{summary['places']:,}")
    metric_cols[1].metric("Destinations", f"{summary['cities']:,}")
    metric_cols[2].metric("Popular cities", f"{summary['popular_destinations']:,}")
    metric_cols[3].metric("Categories", f"{summary['categories']:,}")
    metric_cols[4].metric("Gold clusters", f"{summary['clusters']:,}")

    left, right = st.columns([0.32, 0.68], gap="large")
    with left:
        st.subheader("Plan")
        city_options = [item["city"] for item in cities]
        city = st.selectbox("Destination", options=city_options)
        days = st.slider("Days", 1, 5, 2)
        max_places = st.slider("Places per day", 1, 6, 3)
        selected_categories = st.multiselect("Interests", options=categories, placeholder="All categories")
        generate = st.button("Generate itinerary", type="primary", width="stretch")

        try:
            weather = WEATHER[city] if PORTFOLIO_DEMO_MODE else api_get("/weather/current", city=city)
            weather_cols = st.columns(2)
            weather_cols[0].metric("Temperature", f"{weather['temperature_2m']:.1f} °C")
            weather_cols[1].metric("Wind", f"{weather['wind_speed_10m']:.1f} km/h")
            st.caption(f"Weather: {weather.get('observed_at', 'latest observation')}")
        except (requests.RequestException, KeyError):
            st.caption("Weather is currently unavailable.")

    with right:
        view = st.segmented_control("View", ["Itinerary", "Places", "Destinations"], default="Itinerary", label_visibility="collapsed")
        if view == "Itinerary":
            if not generate:
                st.info("Choose a destination and generate an itinerary.")
            else:
                if PORTFOLIO_DEMO_MODE:
                    itinerary = demo_itinerary(city, days, max_places, selected_categories)
                else:
                    itinerary = api_post("/generate-itinerary", {"city": city, "days": days, "max_places_per_day": max_places, "categories": selected_categories})
                for day in itinerary:
                    st.markdown(f"### Day {day['day']}")
                    if not day["places"]:
                        st.caption("No additional places are available for this day in the selected sample.")
                    for place in day["places"]:
                        st.markdown(
                            f'<div class="place-panel"><strong>{place["start_time"]}–{place["end_time"]} · {place["name"]}</strong><div class="muted">{", ".join(place["categories"][:3])}</div><div>{place.get("address", "")}</div><div class="muted">Related: {", ".join(place["recommendations"])}</div></div>',
                            unsafe_allow_html=True,
                        )
                    day_frame = pd.DataFrame(day["places"])
                    if not day_frame.empty:
                        st.map(day_frame.rename(columns={"lat": "latitude", "lon": "longitude"}))
        elif view == "Places":
            places = demo_places(city, selected_categories) if PORTFOLIO_DEMO_MODE else api_get("/places", city=city, limit=50, categories=selected_categories or None)
            frame = pd.DataFrame(places)
            if frame.empty:
                st.info("No places match the selected filters.")
            else:
                st.map(frame.rename(columns={"lat": "latitude", "lon": "longitude"}))
                st.dataframe(frame[["name", "city", "address", "categories", "website"]], width="stretch", hide_index=True)
        else:
            city_frame = pd.DataFrame(cities)
            st.bar_chart(city_frame.set_index("city")["poi_count"])
            st.dataframe(city_frame, width="stretch", hide_index=True)


def evidence_panel(name: str, role: str, screenshot: str, source: str, service_key: str) -> None:
    st.subheader(name)
    st.write(role)
    action = service_call_to_action(BACKEND_STATUS, SERVICE_REGISTRY[service_key])
    if action is not None:
        st.link_button(action[0], action[1], type="primary", width="stretch")
    st.image(str(SCREENSHOTS / screenshot), width="stretch")
    st.link_button(f"View {name} implementation", f"{REPOSITORY_URL}/blob/dev/{source}", width="stretch")


def pipeline_page() -> None:
    st.title("Pipeline & Storage")
    st.caption("Level 2 · Incremental ETL, medallion layers, analytical processing, and synchronization")
    backend_status_notice()
    st.markdown('<div class="flow"><strong>DATATOURISME</strong> → SHA-256 CDC → <strong>BRONZE</strong> → <strong>SILVER</strong> → SPARK / dbt / H3 / NEO4J</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        evidence_panel("Airflow", "Runs the ordered Bronze → Silver → Spark → Gold → graph → dbt workflow with retries and task visibility.", "03-airflow-dag-grid.png", "airflow/dags/holiday_pipeline_dag.py", "airflow")
        evidence_panel("Spark", "Builds city-level analytical features from trusted Silver data and writes Parquet outputs.", "08-spark-master.png", "src/spark/city_feature_job.py", "spark")
    with right:
        evidence_panel("Postgres", "Stores raw JSONB, normalized relational tables, H3 clusters, and dbt marts.", "16-adminer-postgres-tables.png", "src/gold/postgres_warehouse.py", "adminer")
        st.subheader("dbt analytics layer")
        st.write("Defines staging models, city marts, category marts, schema tests, and source contracts.")
        st.code("dbt run --profiles-dir .\ndbt test --profiles-dir .", language="bash")
        st.link_button("View dbt models", f"{REPOSITORY_URL}/tree/dev/dbt/models", width="stretch")


def serving_page() -> None:
    st.title("Serving, Graph & Events")
    st.caption("Level 1 · Request lifecycle from user intent to a multi-model itinerary response")
    backend_status_notice()
    st.markdown('<div class="flow"><strong>STREAMLIT</strong> → FastAPI → POSTGRES + KMEANS + NEO4J → RESPONSE + KAFKA EVENTS</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        evidence_panel("FastAPI", "Validates contracts, retrieves Silver POIs, runs preference-aware KMeans grouping, and returns itinerary responses.", "02-fastapi-docs.png", "src/api/app.py", "fastapi")
        evidence_panel("Neo4j", "Traverses POI → City and POI → Category relationships to enrich stops with related-place recommendations.", "14-neo4j-browser.png", "src/gold/neo4j_graph_loader.py", "neo4j")
    with right:
        evidence_panel("Streamlit", "Collects preferences and presents itineraries, maps, weather, destinations, and place details.", "01-streamlit-dashboard.png", "src/api/dashboard.py", "streamlit")
        evidence_panel("Kafka", "Publishes weather snapshots and itinerary-generated events without blocking the user request.", "07-kafka-weather-messages.png", "src/streaming/kafka_events.py", "kafka")


def observability_page() -> None:
    st.title("Observability & Product Quality")
    st.caption("Level 3 · Operational telemetry, product-quality metrics, dashboards, and alerts")
    backend_status_notice()
    st.markdown('<div class="flow"><strong>FASTAPI + PIPELINE METRICS</strong> → PROMETHEUS → GRAFANA → ALERTMANAGER</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        evidence_panel("Prometheus", "Scrapes request volume, latency, itinerary quality, weather suitability, route distance, and service health.", "12-prometheus-targets.png", "monitoring/prometheus/prometheus.yml", "prometheus")
    with right:
        evidence_panel("Grafana", "Combines operational and product KPIs into an engineer-facing platform dashboard.", "11-grafana-kpis.png", "monitoring/grafana/dashboards/holiday-platform.json", "grafana")
    st.subheader("Metrics that answer both ‘is it healthy?’ and ‘is it useful?’")
    metric_table = pd.DataFrame(
        [
            ("holiday_api_http_request_duration_seconds", "Operational", "API latency by endpoint"),
            ("holiday_itinerary_category_match_rate", "Product", "Preference alignment"),
            ("holiday_itinerary_avg_distance_km", "Product", "Route efficiency"),
            ("holiday_itinerary_weather_suitability_score", "Product", "Weather-aware suitability"),
        ],
        columns=["Metric", "Domain", "Decision supported"],
    )
    st.dataframe(metric_table, width="stretch", hide_index=True)
    st.link_button("View alert rules", f"{REPOSITORY_URL}/blob/dev/monitoring/prometheus/rules/holiday-alerts.yml")


def runbook_page() -> None:
    st.title("Run the Complete Platform")
    st.caption("Local engineering runbook for reviewers who want to reproduce the backend")
    backend_status_notice()
    st.code("docker compose up --build airflow-init\ndocker compose up --build -d", language="bash")
    st.subheader("Local service map")
    ports = pd.DataFrame(
        [
            ("Streamlit", "8501", "Product dashboard"), ("FastAPI", "8000/docs", "API contract"),
            ("Airflow", "8088", "DAG orchestration"), ("Kafka UI", "8090", "Topics and consumers"),
            ("Spark", "8080", "Cluster and jobs"), ("Grafana", "3000", "KPI dashboards"),
            ("Prometheus", "9090", "Metrics and targets"), ("Adminer", "5050", "Postgres inspection"),
        ],
        columns=["Service", "Local port", "Purpose"],
    )
    st.dataframe(ports, width="stretch", hide_index=True)
    st.link_button("Read the full repository guide", REPOSITORY_URL)


HOME_PAGE = st.Page(home_page, title="Project Home", icon="🏠", default=True)
APP_PAGE = st.Page(itinerary_page, title="Itinerary App", icon="🧭")
PIPELINE_PAGE = st.Page(pipeline_page, title="Pipeline & Storage", icon="🔄")
SERVING_PAGE = st.Page(serving_page, title="Serving & Graph", icon="🔌")
OBSERVABILITY_PAGE = st.Page(observability_page, title="Observability", icon="📊")
RUNBOOK_PAGE = st.Page(runbook_page, title="Runbook", icon="📘")

navigation = st.navigation(
    {
        "Start": [HOME_PAGE],
        "Explore": [APP_PAGE, PIPELINE_PAGE, SERVING_PAGE, OBSERVABILITY_PAGE, RUNBOOK_PAGE],
    }
)
navigation.run()
