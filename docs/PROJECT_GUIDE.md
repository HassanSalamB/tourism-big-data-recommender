# Holiday Itinerary Data Platform — Project Guide

This guide explains how the repository turns raw DATAtourisme records into an interactive, observable itinerary product.

![Platform architecture](assets/holiday-platform-architecture.png)

## Level 1 — Request serving

The request-serving layer turns user intent into a multi-model itinerary response.

1. Streamlit sends `city`, `days`, `max_places_per_day`, and preferred categories.
2. FastAPI validates the request contract and loads candidate POIs from `silver_places`.
3. Runtime KMeans groups coordinates into geographically practical days.
4. Categories act as weighted preferences instead of rigid filters, preserving itinerary variety.
5. Neo4j traverses `POI → City` and `POI → Category` relationships to add related-place suggestions.
6. The API returns the itinerary, publishes a Kafka event, and updates Prometheus metrics.

### API catalog

| Endpoint | Method | Responsibility |
|---|---|---|
| `/health` | GET | Service and dependency health |
| `/summary` | GET | Dataset volume statistics |
| `/cities` | GET | Available destinations |
| `/categories` | GET | POI taxonomy |
| `/places` | GET | Filterable POI metadata |
| `/weather/current` | GET | Open-Meteo conditions and weather event |
| `/generate-itinerary` | POST | Multi-model itinerary generation and event |

Implementation: [`src/api/app.py`](../src/api/app.py), [`src/api/dashboard.py`](../src/api/dashboard.py)

## Level 2 — Incremental ETL

The pipeline separates durability, trust, and consumption through Bronze, Silver, and Gold responsibilities.

### Bronze — preserve and detect change

- Downloads the DATAtourisme ZIP feed.
- Skips unchanged archives using source metadata.
- Stores raw payloads as Postgres JSONB.
- Compares SHA-256 `content_hash` values so only new or changed records are updated.

### Silver — normalize and validate

- Processes source JSON in Pandas chunks.
- Uses extraction paths from `config.yaml` instead of hard-coded source paths.
- Builds relational places, categories, place-category links, timings, and prices.
- Writes a Parquet snapshot for analytical processing.

### Gold — synchronize specialized outputs

- Builds H3 spatial clusters for analytical summaries and heat maps.
- Uses `updated_at`, `neo4j_synced_at`, and `gold_pg_synced_at` for incremental downstream synchronization.
- Loads POI, city, and category relationships into Neo4j.
- Runs Spark city-feature aggregation and dbt marts/tests.

Airflow coordinates the ordered execution and exposes task status, retries, and logs.

Implementation: [`airflow/dags/holiday_pipeline_dag.py`](../airflow/dags/holiday_pipeline_dag.py), [`src/pipeline.py`](../src/pipeline.py), [`dbt/models`](../dbt/models)

## Level 3 — Observability

![Three platform levels](assets/holiday-platform-three-levels.png)

Prometheus captures both operational health and product usefulness.

| Metric | Question answered |
|---|---|
| `holiday_api_http_requests_total` | How much traffic reaches each endpoint? |
| `holiday_api_http_request_duration_seconds` | Where is request latency increasing? |
| `holiday_itinerary_category_match_rate` | Do results reflect selected preferences? |
| `holiday_itinerary_avg_distance_km` | Are generated routes geographically efficient? |
| `holiday_itinerary_weather_suitability_score` | Do recommendations fit current conditions? |

Grafana visualizes these signals, while Alertmanager evaluates rules for operational failures.

Implementation: [`monitoring/prometheus`](../monitoring/prometheus), [`monitoring/grafana`](../monitoring/grafana)

## Recorded backend evidence

The public Render service runs the Streamlit portfolio. The full infrastructure is reproduced with Docker Compose and documented through real execution screenshots:

- [Airflow DAG](../artifacts/screenshots/03-airflow-dag-grid.png)
- [Kafka messages](../artifacts/screenshots/07-kafka-weather-messages.png)
- [Spark master](../artifacts/screenshots/08-spark-master.png)
- [Postgres tables](../artifacts/screenshots/16-adminer-postgres-tables.png)
- [Neo4j browser](../artifacts/screenshots/14-neo4j-browser.png)
- [FastAPI docs](../artifacts/screenshots/02-fastapi-docs.png)
- [Prometheus targets](../artifacts/screenshots/12-prometheus-targets.png)
- [Grafana KPIs](../artifacts/screenshots/11-grafana-kpis.png)

## Run the complete stack

```bash
docker compose up --build airflow-init
docker compose up --build -d
```

See the root [README](../README.md) for the service links and quick start.
