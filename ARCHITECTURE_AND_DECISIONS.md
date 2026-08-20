# Architecture And Decisions

This document explains the integrated data-platform architecture and the main decisions behind each tool.

## Project Goal

The project prepares DATAtourisme POI data for an itinerary application. The app should support destination exploration, category preferences, weather-aware planning, graph-based related places, and platform-level observability.

## Current Architecture

```text
DATAtourisme feed
  -> Airflow orchestration
  -> Bronze ZIP download
  -> Bronze content-hash change detection
  -> Bronze Postgres JSONB
  -> Silver Postgres relational tables cleaned with pandas chunks
  -> Spark city feature generation
  -> Gold Postgres clusters
  -> dbt analytics marts and tests
  -> Neo4j POI graph
  -> FastAPI service
  -> Streamlit dashboard

Open-Meteo current weather
  -> FastAPI weather endpoint
  -> Kafka weather_snapshots topic
  -> Prometheus metrics
  -> Grafana KPIs
```

The full local platform is started with:

```bash
docker compose up --build
```

The stack includes Postgres, Neo4j, Kafka, Spark, Airflow, dbt, FastAPI, Streamlit, Prometheus, and Grafana.

## Why These Tools Are Used

- Airflow: makes pipeline scheduling, retries, task ordering, and run visibility explicit.
- Postgres: stores local bronze, silver, gold, and dbt marts in one practical database.
- Neo4j: models POI, city, and category relationships for related-place recommendations.
- Kafka: captures live platform events such as weather snapshots and generated itinerary requests.
- Spark: builds city-level feature aggregates from Parquet snapshots, giving the project a scalable batch-processing path.
- dbt: owns SQL marts and data tests so analytics logic is documented and repeatable.
- Snowflake: provides the cloud warehouse target for the same dbt models when the project needs shared analytics or BI.
- Terraform: defines cloud infrastructure such as Snowflake databases, warehouses, schemas, and future managed services.
- Prometheus: scrapes API/product metrics from `/metrics`.
- Grafana: visualizes operational and product KPIs from Prometheus.

## Orchestration Layer

Airflow is the pipeline orchestrator. The DAG is:

```text
airflow/dags/holiday_pipeline_dag.py
```

Pipeline order:

```text
bronze_download_zip
  -> bronze_detect_and_load_changes
  -> silver_normalize
  -> spark_city_features
  -> gold_postgres
  -> neo4j_graph
  -> dbt_run_and_test
```

Decision:

- Airflow is the only scheduler in the active Docker Compose stack.
- The original `src/pipeline.py` remains the reusable command-line entrypoint for each stage.
- The bronze download and bronze change-detection/load steps are separate Airflow tasks, so download progress and hash comparison results are visible independently.
- dbt and Spark are invoked by Airflow so they are part of the actual pipeline path.

## Bronze Layer

Files:

```text
src/bronze/data_api.py
src/bronze/bronze_loader.py
```

Primary table:

```text
bronze_raw_poi
```

Bronze responsibilities:

- download the DATAtourisme ZIP feed
- stream ZIP JSON entries instead of loading the full archive into memory
- store raw POI JSON in Postgres `JSONB`
- compute a stable SHA-256 `content_hash`
- insert new rows and update only changed rows

Decision:

- Postgres JSONB keeps the raw source replayable without adding another document database.
- Hash comparison makes incremental ingestion cheap and auditable.

## Silver Layer

File:

```text
src/silver/data_normalizer.py
```

Primary tables:

```text
silver_places
silver_categories
silver_place_categories
silver_timings
silver_prices
```

Silver responsibilities:

- read changed bronze rows by comparing source hashes
- extract nested DATAtourisme fields using mappings in `config.yaml`
- normalize places, categories, timings, and prices
- validate required fields and coordinate ranges
- write a Parquet snapshot for Spark and portable downstream processing

Decision:

- pandas remains the right local tool for irregular JSON normalization.
- Spark is used after silver, where the data is already structured and easier to aggregate.

## Spark Feature Layer

File:

```text
src/spark/city_feature_job.py
```

Output:

```text
data/gold/spark/city_features
```

Spark responsibilities:

- read the silver Parquet snapshot
- generate city-level aggregates such as place counts, region counts, and average coordinates
- provide a scalable feature-generation path for future ranking and ML work

Spark resource configuration:

```text
SPARK_WORKER_CORES=2
SPARK_WORKER_MEMORY=2G
SPARK_DRIVER_MEMORY=1g
SPARK_EXECUTOR_MEMORY=1g
SPARK_EXECUTOR_CORES=1
SPARK_SQL_SHUFFLE_PARTITIONS=8
```

These values are intentionally small for a laptop-friendly local cluster. Worker settings are applied in Docker Compose, while driver/executor/shuffle settings are applied when `src/spark/city_feature_job.py` creates the `SparkSession`.

Decision:

- Spark is justified for batch feature generation and future growth.
- It is not used for the first-pass JSON cleanup because the existing pandas code is simpler and more precise for that step.

## Gold Postgres Layer

File:

```text
src/gold/postgres_warehouse.py
```

Primary table:

```text
gold_clusters
```

Gold responsibilities:

- compute H3 cluster IDs
- calculate category-based scores
- write cluster summaries for exploration and reporting
- mark synced silver rows with `gold_pg_synced_at`

Decision:

- `gold_clusters` is an analytics layer, not the live itinerary selector.
- Live itineraries still use actual POIs from `silver_places`.

## dbt Analytics Layer

Files:

```text
dbt/dbt_project.yml
dbt/profiles.yml
dbt/models/staging/
dbt/models/marts/
```

Current models:

```text
stg_places
stg_categories
stg_place_categories
mart_city_summary
mart_city_category_summary
```

dbt responsibilities:

- turn silver data into reusable analytics marts
- run data tests for unique IDs and required fields
- provide a Snowflake target for cloud warehouse runs

Decision:

- dbt owns SQL transformations and tests.
- Python owns API ingestion, nested JSON parsing, and graph loading.

## Neo4j Graph Layer

File:

```text
src/gold/neo4j_graph_loader.py
```

Graph model:

```text
(:POI)-[:LOCATED_IN]->(:City)
(:POI)-[:HAS_CATEGORY]->(:Category)
```

Neo4j responsibilities:

- maintain POI, City, and Category nodes
- refresh relationships for changed POIs
- support related-place suggestions in the itinerary API

Decision:

- Graph traversal is a better fit than SQL joins for related-place discovery.
- Geographic map data still comes from Postgres because coordinates are tabular.

## Kafka Streaming Layer

Code:

```text
src/streaming/kafka_events.py
```

Topics:

```text
weather_snapshots
itinerary_requests
```

Kafka responsibilities:

- receive current weather snapshots requested by users
- receive itinerary generation events
- create a stream of product behavior that can later feed Spark, dbt marts, or model evaluation

Decision:

- Kafka is used for event-shaped data, not the DATAtourisme ZIP batch feed.
- API requests do not fail if Kafka briefly restarts; failures are counted in Prometheus.

## FastAPI And Streamlit App Layer

Files:

```text
src/api/app.py
src/api/dashboard.py
```

FastAPI responsibilities:

- expose dashboard JSON endpoints
- run request-time KMeans itinerary grouping
- query Neo4j for related POI suggestions
- request current weather from Open-Meteo
- publish weather and itinerary events to Kafka
- expose Prometheus metrics at `/metrics`

Streamlit responsibilities:

- provide the dashboard UI
- call FastAPI over HTTP
- show data metrics, maps, generated itineraries, and city weather

Weather endpoint:

```text
GET /weather/current?city=Paris
```

Decision:

- Open-Meteo is used because it provides current weather by latitude/longitude without an API key.
- City coordinates come from the average lat/lon of matching `silver_places`.
- Weather is useful for future itinerary scoring, such as preferring indoor places during rain.

## Observability Layer

Files:

```text
monitoring/prometheus/prometheus.yml
monitoring/grafana/provisioning/
monitoring/grafana/dashboards/holiday-platform.json
```

Metrics exposed by FastAPI:

```text
holiday_api_http_requests_total
holiday_api_http_request_duration_seconds
holiday_itineraries_generated_total
holiday_itinerary_places_selected_total
holiday_weather_requests_total
holiday_kafka_events_total
holiday_itinerary_category_match_rate
holiday_itinerary_avg_distance_km
holiday_itinerary_avg_recommendations
holiday_itinerary_weather_suitability_score
```

Prometheus responsibilities:

- scrape API health and product metrics
- track Kafka publish success/failure counts
- track itinerary generation volume and latency
- track itinerary quality signals such as preference match, route compactness, graph recommendation density, and weather suitability

Grafana responsibilities:

- visualize API request rate
- visualize generated itineraries by city
- visualize average API latency
- visualize Kafka event publishing status

Decision:

- Prometheus/Grafana are used for both operational reliability and product KPI monitoring.
- These metrics make the app easier to defend technically because performance and user activity are measurable.

## Snowflake And Terraform

Snowflake is configured as a dbt target in:

```text
dbt/profiles.yml
```

Terraform starter files:

```text
terraform/examples/snowflake/
```

Decision:

- local development uses Postgres
- Snowflake is the warehouse target for cloud analytics
- Terraform makes Snowflake resources reproducible instead of manually created

## Service Ports

```text
FastAPI:     http://localhost:8000/docs
Streamlit:   http://localhost:8501
Airflow:     http://localhost:8088
Prometheus:  http://localhost:9090
Grafana:     http://localhost:3000
Spark UI:    http://localhost:8080
Adminer:     http://localhost:5050
Neo4j:       http://localhost:7474
Postgres:    localhost:5432
Kafka:       localhost:9094 externally, kafka:9092 inside Docker
Kafka UI:    http://localhost:8090
```

## Current Pipeline Files

```text
src/pipeline.py
src/bronze/data_api.py
src/bronze/bronze_loader.py
src/silver/data_normalizer.py
src/spark/city_feature_job.py
src/gold/postgres_warehouse.py
src/gold/neo4j_graph_loader.py
src/streaming/kafka_events.py
src/api/app.py
src/api/dashboard.py
airflow/dags/holiday_pipeline_dag.py
dbt/dbt_project.yml
docker-compose.yml
Dockerfile.airflow
monitoring/prometheus/prometheus.yml
monitoring/grafana/dashboards/holiday-platform.json
terraform/examples/snowflake/
```
