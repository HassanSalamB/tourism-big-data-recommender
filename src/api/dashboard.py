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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = PROJECT_ROOT / "artifacts" / "screenshots"
ARCHITECTURE = PROJECT_ROOT / "docs" / "holiday-platform-architecture.svg"
REPOSITORY_URL = "https://github.com/HassanSalamB/tourism-big-data-recommender"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PORTFOLIO_DEMO_MODE = os.getenv("PORTFOLIO_DEMO_MODE", "false").lower() in {"1", "true", "yes"}


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
            '<div class="notice"><strong>Public portfolio mode.</strong> The interface uses a small curated dataset so the original Streamlit experience remains interactive on Render. The complete DATAtourisme pipeline and backend services are demonstrated with real execution evidence under <strong>Backend Services</strong>.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="live-note"><strong>Full-stack mode.</strong> Connected to the FastAPI service at <code>{API_BASE_URL}</code>.</div>',
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

    st.subheader("Explore the project")
    cols = st.columns(3)
    with cols[0]:
        st.markdown('<div class="card"><h3>🧭 Live itinerary app</h3><p>Choose a destination and interests, generate a multi-day plan, inspect places, maps, and weather.</p></div>', unsafe_allow_html=True)
        st.page_link(APP_PAGE, label="Open Streamlit experience", icon="↗️")
    with cols[1]:
        st.markdown('<div class="card"><h3>⚙️ Backend services</h3><p>Review real Airflow, Kafka, Spark, Postgres, Neo4j, FastAPI, Prometheus, and Grafana evidence.</p></div>', unsafe_allow_html=True)
        st.page_link(BACKEND_PAGE, label="Tour backend evidence", icon="↗️")
    with cols[2]:
        st.markdown('<div class="card"><h3>🗺️ Architecture map</h3><p>Follow data from source ingestion through Bronze, Silver, Gold, APIs, streaming, and observability.</p></div>', unsafe_allow_html=True)
        st.page_link(ARCHITECTURE_PAGE, label="View the full process", icon="↗️")

    st.subheader("End-to-end system map")
    st.image(str(ARCHITECTURE), use_container_width=True)
    st.caption("Airflow coordinates the batch path; Kafka carries events; Prometheus and Grafana close the operational feedback loop.")

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


SERVICES = [
    ("Airflow", "Orchestrates Bronze → Silver → Spark → Gold → graph → dbt", "03-airflow-dag-grid.png", "airflow/dags/holiday_pipeline_dag.py"),
    ("Kafka", "Carries weather snapshots and itinerary request events", "07-kafka-weather-messages.png", "src/streaming/kafka_events.py"),
    ("Spark", "Builds distributed city feature outputs", "08-spark-master.png", "src/spark/city_feature_job.py"),
    ("Postgres", "Stores raw JSONB, normalized relations, clusters, and marts", "16-adminer-postgres-tables.png", "src/gold/postgres_warehouse.py"),
    ("Neo4j", "Models POI, city, and category relationships", "14-neo4j-browser.png", "src/gold/neo4j_graph_loader.py"),
    ("FastAPI", "Serves places, destinations, weather, and itineraries", "02-fastapi-docs.png", "src/api/app.py"),
    ("Prometheus", "Scrapes API and pipeline health metrics", "12-prometheus-targets.png", "monitoring/prometheus/prometheus.yml"),
    ("Grafana", "Visualizes operational and product KPIs", "11-grafana-kpis.png", "monitoring/grafana/dashboards/holiday-platform.json"),
]


def backend_page() -> None:
    st.title("Backend Services")
    st.caption("Recorded execution evidence from the complete Docker Compose platform")
    st.markdown('<div class="notice"><strong>Honest deployment boundary.</strong> The public Render service hosts Streamlit. The infrastructure below runs through the repository’s Docker Compose environment; each panel links to its implementation and shows evidence from a real local run.</div>', unsafe_allow_html=True)
    st.markdown('<div class="flow"><strong>INGEST</strong> → <strong>ORCHESTRATE</strong> → <strong>TRANSFORM</strong> → <strong>MODEL</strong> → <strong>SERVE</strong> → <strong>OBSERVE</strong></div>', unsafe_allow_html=True)

    for index in range(0, len(SERVICES), 2):
        columns = st.columns(2)
        for column, service in zip(columns, SERVICES[index : index + 2]):
            name, role, screenshot, source = service
            with column:
                st.subheader(name)
                st.write(role)
                st.image(str(SCREENSHOTS / screenshot), use_container_width=True)
                st.link_button(f"View {name} implementation", f"{REPOSITORY_URL}/blob/dev/{source}", width="stretch")


def architecture_page() -> None:
    st.title("Architecture & Data Flow")
    st.caption("The complete process map for the original Holiday Itinerary Data Platform")
    st.image(str(ARCHITECTURE), use_container_width=True)
    st.markdown(
        """
        ### How to read the platform

        1. **DATAtourisme** lands as immutable Bronze JSONB with content hashes for change detection.
        2. **Silver** normalization creates queryable places, categories, timings, and prices.
        3. **Spark, dbt, Postgres, and Neo4j** create analytical and relationship-aware Gold outputs.
        4. **FastAPI and Streamlit** turn those outputs into itinerary and exploration products.
        5. **Kafka, Prometheus, Grafana, and Alertmanager** expose events, health, KPIs, and failures.
        """
    )
    st.link_button("Open architecture source", f"{REPOSITORY_URL}/blob/dev/architecture.mmd")


def runbook_page() -> None:
    st.title("Run the Complete Platform")
    st.caption("Local engineering runbook for reviewers who want to reproduce the backend")
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
BACKEND_PAGE = st.Page(backend_page, title="Backend Services", icon="⚙️")
ARCHITECTURE_PAGE = st.Page(architecture_page, title="Architecture", icon="🗺️")
RUNBOOK_PAGE = st.Page(runbook_page, title="Runbook", icon="📘")

navigation = st.navigation({"Start": [HOME_PAGE], "Explore": [APP_PAGE, BACKEND_PAGE, ARCHITECTURE_PAGE, RUNBOOK_PAGE]})
navigation.run()
