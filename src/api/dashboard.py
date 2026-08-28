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
PROCESSING_ARCHITECTURE = PROJECT_ROOT / "docs" / "assets" / "level-2-spark-dbt-architecture.svg"
REPOSITORY_URL = "https://github.com/HassanSalamB/tourism-big-data-recommender"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PORTFOLIO_DEMO_MODE = os.getenv("PORTFOLIO_DEMO_MODE", "false").lower() in {"1", "true", "yes"}
BACKEND_STATUS = load_backend_status()
SERVICE_REGISTRY = load_service_registry()


st.set_page_config(page_title="Accommodation Intelligence Lab", page_icon="🧭", layout="wide")
st.markdown(
    """
    <style>
      .block-container {max-width: 1280px; padding-top: 1.25rem; padding-bottom: 3rem;}
      [data-testid="stSidebar"] {border-right: 1px solid #dce7e4; background:#f7faf9;}
      [data-testid="stMetric"] {border: 1px solid #dce5e3; border-radius: 12px; padding: 12px 16px; background: #fff;}
      .hero {padding: 34px 40px; border-radius: 22px; color: #effaf7; background: radial-gradient(circle at 92% 8%,rgba(54,211,172,.18),transparent 32%),linear-gradient(135deg,#061721,#0a3c3a); margin:.35rem 0 .8rem; box-shadow:0 18px 45px rgba(5,28,35,.14);}
      .hero small {color:#67d4b8; font-weight:700; letter-spacing:.16em;}
      .hero h2 {color:#fff; font-size:2.25rem; line-height:1.12; margin:.55rem 0 .65rem; max-width:900px;}
      .hero p {color:#c9ddda; font-size:1.02rem; line-height:1.58; max-width:900px; margin:0;}
      .demo-focus {text-align:center; padding:6px 0 10px;}
      .demo-focus h3 {font-size:1.35rem; color:#123d3a; margin:.15rem 0 .15rem;}
      .demo-focus p {color:#61736f; margin:0 auto .45rem; max-width:680px; line-height:1.45;}
      .command-strip {display:grid; grid-template-columns:repeat(4,1fr); gap:1px; overflow:hidden; margin:.7rem 0 1.5rem; border:1px solid #d7e5e1; border-radius:16px; background:#d7e5e1;}
      .command-cell {background:#fff; padding:16px 18px;}
      .command-cell span {display:block; color:#71827f; font-size:.7rem; font-weight:800; letter-spacing:.11em; text-transform:uppercase;}
      .command-cell strong {display:block; color:#123d3a; font-size:1.08rem; margin-top:.22rem;}
      .section-lead {max-width:850px; color:#60736f; margin-top:-.35rem; margin-bottom:1rem;}
      .level-card {min-height:150px; padding:20px; border:1px solid #d7e5e1; border-radius:16px; background:#fff; box-shadow:0 10px 28px rgba(9,48,47,.06);}
      .level-card small {color:#0a826b; font-weight:800; letter-spacing:.1em;}
      .level-card h3 {color:#123d3a; font-size:1.05rem; margin:.55rem 0 .38rem;}
      .level-card p {color:#5f716e; font-size:.88rem; line-height:1.5; margin:0;}
      .card {min-height:145px; padding:20px; border:1px solid #dce6e3; border-radius:16px; background:#f8fbfa;}
      .card h3 {font-size:1.08rem; color:#123d3a; margin:0 0 .5rem;}
      .card p {font-size:.92rem; color:#536765; margin:0;}
      .stage {min-height:168px; padding:22px; border:1px solid #d9e7e3; border-radius:18px; background:linear-gradient(180deg,#ffffff,#f5faf8);}
      .stage-number {display:inline-block; color:#087862; background:#dff5ee; border-radius:999px; padding:4px 10px; font-size:.76rem; font-weight:800; letter-spacing:.08em;}
      .stage h3 {font-size:1.05rem; color:#103b38; margin:.75rem 0 .45rem;}
      .stage p {font-size:.9rem; line-height:1.55; color:#5c706c; margin:0;}
      .reviewer-note {padding:20px 22px; border-left:5px solid #19a984; border-radius:12px; background:#edf9f5; margin:.7rem 0 1.2rem; color:#244d47;}
      .eyebrow {font-size:.78rem; color:#087862; font-weight:800; letter-spacing:.13em; text-transform:uppercase; margin-bottom:.3rem;}
      .notice {padding:13px 17px; border-radius:12px; background:#fff7e5; border:1px solid #ead49c; margin:.5rem 0 1rem;}
      .live-note {padding:13px 17px; border-radius:12px; background:#eaf7f3; border:1px solid #aed9cd; margin:.5rem 0 1rem;}
      .place-panel {border:1px solid #d8e1df; border-radius:10px; padding:.8rem 1rem; margin-bottom:.75rem; background:#fff;}
      .muted {color:#667875; font-size:.9rem;}
      .flow {padding:18px; border-radius:15px; background:#0b222b; color:#eaf5f2; line-height:2; text-align:center; margin:1rem 0;}
      .flow strong {color:#69d5b9;}
      .architecture-caption {color:#5f716e; font-size:.95rem; line-height:1.55; margin:.15rem 0 1rem;}
      @media (max-width: 640px) {
        .block-container {padding-top:1rem;}
        .hero {padding:24px 22px; border-radius:19px;}
        .hero h2 {font-size:1.75rem; line-height:1.16;}
        .hero p {font-size:.98rem; line-height:1.55;}
        .stage {min-height:auto; margin-bottom:.6rem;}
        .command-strip {grid-template-columns:repeat(2,1fr);}
      }
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
    st.title("Accommodation Intelligence Lab")
    st.caption("A decision-ready tourism data product and end-to-end data engineering portfolio")
    st.markdown(
        """
        <div class="hero">
          <small>TOURISM INTELLIGENCE · DATA PRODUCTS · PLATFORM OPERATIONS</small>
          <h2>Turning fragmented destination data into decisions travelers and accommodation teams can use</h2>
          <p>This lab converts French tourism supply data into trusted geographic features, explainable recommendations,
          itinerary APIs, operational events, and monitored decision signals—showing the full path from raw data to a usable product.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="demo-focus">
          <h3>Live product demo</h3>
          <p>Open the Streamlit itinerary app first, then inspect the architecture and backend evidence if you want to go deeper.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    live_left, live_center, live_right = st.columns([0.28, 0.44, 0.28])
    with live_center:
        st.page_link(APP_PAGE, label="Open live itinerary demo", icon="🧭", width="stretch")

    st.subheader("Complete system architecture")
    st.markdown(
        '<p class="architecture-caption">This is the end-to-end view: ingestion, orchestration, medallion storage, Spark/dbt processing, graph enrichment, serving, streaming events and observability.</p>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.image(str(ARCHITECTURE_HERO), width="stretch")

    st.markdown(
        f"""
        <div class="command-strip">
          <div class="command-cell"><span>Product</span><strong>Live on Render</strong></div>
          <div class="command-cell"><span>Backend</span><strong>{BACKEND_STATUS.title()} evidence</strong></div>
          <div class="command-cell"><span>Data contract</span><strong>Bronze → Silver → Gold</strong></div>
          <div class="command-cell"><span>Platform scope</span><strong>18 coordinated services</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    quick_actions = st.columns([1, 1, 1])
    with quick_actions[0]:
        st.page_link(ARCHITECTURE_PAGE, label="View architecture details", icon="🧱", width="stretch")
    with quick_actions[1]:
        st.page_link(PIPELINE_PAGE, label="Inspect backend evidence", icon="🔄", width="stretch")
    with quick_actions[2]:
        st.link_button("Review source on GitHub", REPOSITORY_URL, icon="↗", width="stretch")

    st.markdown("### From source data to a decision")
    stages = st.columns(4)
    stage_content = [
        ("01 · INGEST", "Capture change", "Airflow ingests DATAtourisme archives and SHA-256 change detection prevents unnecessary reprocessing."),
        ("02 · TRUST", "Build governed layers", "Bronze preserves raw JSONB; Silver normalizes entities; Gold creates H3 and city-level analytical features."),
        ("03 · DECIDE", "Generate intelligence", "PostgreSQL, KMeans, weather and Neo4j relationships produce explainable destination recommendations."),
        ("04 · LEARN", "Observe outcomes", "Kafka events and Prometheus metrics expose usage, latency, category match, route distance and weather suitability."),
    ]
    for column, (number, heading, description) in zip(stages, stage_content):
        with column:
            st.markdown(
                f'<div class="stage"><span class="stage-number">{number}</span><h3>{heading}</h3><p>{description}</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="reviewer-note">
          <div class="eyebrow">Reviewer context</div>
          <strong>Why this is relevant to accommodation intelligence:</strong> the project demonstrates the same engineering pattern—combine fragmented market signals, create governed features, serve explainable recommendations, and monitor whether the product is useful. It uses public tourism-supply data rather than proprietary hotel pricing or demand data.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Open the product or inspect the engineering evidence")
    status_columns = st.columns([0.22, 0.78])
    status_columns[0].metric("Backend evidence", BACKEND_STATUS.title())
    status_columns[1].info("The interactive product runs live on Render. Backend panels use screenshots captured from verified full-stack executions until the dedicated engineering environment is online.")
    cols = st.columns(4)
    with cols[0]:
        st.image(str(SCREENSHOTS / "01-streamlit-dashboard.png"), width="stretch")
        st.page_link(APP_PAGE, label="Use the itinerary product", icon="🧭", width="stretch")
    with cols[1]:
        st.image(str(SCREENSHOTS / "03-airflow-dag-grid.png"), width="stretch")
        st.page_link(PIPELINE_PAGE, label="Inspect Airflow & storage", icon="🔄", width="stretch")
    with cols[2]:
        st.image(str(SCREENSHOTS / "02-fastapi-docs.png"), width="stretch")
        st.page_link(SERVING_PAGE, label="Inspect API, graph & Kafka", icon="🔌", width="stretch")
    with cols[3]:
        st.image(str(SCREENSHOTS / "11-grafana-kpis.png"), width="stretch")
        st.page_link(OBSERVABILITY_PAGE, label="Inspect Grafana & metrics", icon="📊", width="stretch")

    st.subheader("What a reviewer can validate")
    capabilities = st.columns(4)
    capabilities[0].metric("Architecture", "18 services")
    capabilities[1].metric("Data quality", "Bronze → Gold")
    capabilities[2].metric("Data product", "API + UI")
    capabilities[3].metric("Operations", "Events + SLOs")


def architecture_page() -> None:
    st.title("Architecture Details")
    st.caption("Detailed platform design for reviewers who want levels, processing flow, and validation path")
    backend_status_notice()

    st.markdown("### Complete system topology")
    st.markdown(
        '<p class="architecture-caption">The top-level architecture connects the user-facing product to the data platform and engineering evidence behind it.</p>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.image(str(ARCHITECTURE_HERO), width="stretch")

    overview_tab, processing_tab, validation_tab = st.tabs(["Architecture levels", "Spark + dbt layer", "Reviewer path"])

    with overview_tab:
        st.subheader("Three engineering levels")
        st.markdown(
            '<p class="section-lead">Level 1 serves the product, Level 2 builds governed decision features, and Level 3 measures reliability and product quality.</p>',
            unsafe_allow_html=True,
        )
        st.image(str(LEVELS_OVERVIEW), width="stretch")
        level_columns = st.columns(3)
        level_content = [
            ("LEVEL 1", "Request serving", "Streamlit captures intent; FastAPI combines PostgreSQL, runtime clustering and Neo4j context."),
            ("LEVEL 2", "Processing & analytics", "Airflow governs incremental ETL while Spark and dbt build complementary decision features."),
            ("LEVEL 3", "Observability", "Prometheus, Grafana and Alertmanager track both service health and product usefulness."),
        ]
        for column, (level, heading, description) in zip(level_columns, level_content):
            with column:
                st.markdown(f'<div class="level-card"><small>{level}</small><h3>{heading}</h3><p>{description}</p></div>', unsafe_allow_html=True)

    with processing_tab:
        st.subheader("Level 2: Spark + dbt")
        st.markdown(
            '<p class="section-lead">Spark and dbt are not duplicate tools: Spark performs scalable feature computation over trusted snapshots; dbt produces tested SQL marts and explicit analytical contracts.</p>',
            unsafe_allow_html=True,
        )
        st.image(str(PROCESSING_ARCHITECTURE), width="stretch")
        spark_col, dbt_col = st.columns(2)
        with spark_col:
            st.markdown('<div class="card"><h3>Apache Spark</h3><p>Computes destination and city-level features from trusted Silver data, then writes analytical snapshots for downstream models and marts.</p></div>', unsafe_allow_html=True)
        with dbt_col:
            st.markdown('<div class="card"><h3>dbt</h3><p>Turns warehouse tables into tested marts with documented contracts, making Gold outputs easier to validate and reuse.</p></div>', unsafe_allow_html=True)

    with validation_tab:
        st.subheader("Recommended reviewer path")
        st.write("Start with the live itinerary app, then inspect the evidence pages that map each product capability to the backend implementation.")
        path_cols = st.columns(4)
        with path_cols[0]:
            st.page_link(APP_PAGE, label="Live demo", icon="🧭", width="stretch")
        with path_cols[1]:
            st.page_link(PIPELINE_PAGE, label="Pipeline evidence", icon="🔄", width="stretch")
        with path_cols[2]:
            st.page_link(SERVING_PAGE, label="Serving evidence", icon="🔌", width="stretch")
        with path_cols[3]:
            st.page_link(OBSERVABILITY_PAGE, label="Observability", icon="📊", width="stretch")


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
        view = st.segmented_control("View", ["Itinerary", "Map & places", "Destinations"], default="Itinerary", label_visibility="collapsed")
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
                    day_frame = pd.DataFrame(day["places"])
                    if not day_frame.empty:
                        st.caption(f"Day {day['day']} route map · zoom or open fullscreen to explore")
                        st.map(day_frame.rename(columns={"lat": "latitude", "lon": "longitude"}))
                    for place in day["places"]:
                        st.markdown(
                            f'<div class="place-panel"><strong>{place["start_time"]}–{place["end_time"]} · {place["name"]}</strong><div class="muted">{", ".join(place["categories"][:3])}</div><div>{place.get("address", "")}</div><div class="muted">Related: {", ".join(place["recommendations"])}</div></div>',
                            unsafe_allow_html=True,
                        )
        elif view == "Map & places":
            places = demo_places(city, selected_categories) if PORTFOLIO_DEMO_MODE else api_get("/places", city=city, limit=50, categories=selected_categories or None)
            frame = pd.DataFrame(places)
            if frame.empty:
                st.info("No places match the selected filters.")
            else:
                st.subheader(f"Explore {city} on the map")
                st.caption("Zoom, pan, or open fullscreen; the table below provides the corresponding place details.")
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
    st.subheader("Processing and analytics architecture")
    st.write("Spark and dbt branch from the trusted Silver layer, solve different transformation problems, and converge in the Gold decision layer.")
    with st.container(border=True):
        st.image(str(PROCESSING_ARCHITECTURE), width="stretch")
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
ARCHITECTURE_PAGE = st.Page(architecture_page, title="Architecture Details", icon="🧱")
PIPELINE_PAGE = st.Page(pipeline_page, title="Pipeline & Storage", icon="🔄")
SERVING_PAGE = st.Page(serving_page, title="Serving & Graph", icon="🔌")
OBSERVABILITY_PAGE = st.Page(observability_page, title="Observability", icon="📊")
RUNBOOK_PAGE = st.Page(runbook_page, title="Runbook", icon="📘")

navigation = st.navigation(
    {
        "Start": [HOME_PAGE],
        "Explore": [APP_PAGE, ARCHITECTURE_PAGE, PIPELINE_PAGE, SERVING_PAGE, OBSERVABILITY_PAGE, RUNBOOK_PAGE],
    }
)
navigation.run()
