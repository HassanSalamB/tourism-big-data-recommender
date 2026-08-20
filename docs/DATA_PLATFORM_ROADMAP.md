# Data Platform Roadmap

This project now treats Airflow, Kafka, Spark, dbt, Terraform, Snowflake, Prometheus, and Grafana as first-class parts of the platform design. Each tool has a concrete role and a clear reason for being in the architecture.

## Integrated Architecture

```text
DATAtourisme feed
  -> Airflow orchestration
  -> Bronze ZIP download
  -> Bronze content-hash change detection
  -> Bronze Postgres JSONB
  -> Silver normalization + Parquet snapshot
  -> Spark city feature generation
  -> Gold Postgres clusters
  -> dbt marts and tests
  -> Neo4j graph
  -> FastAPI + Streamlit

Weather API
  -> FastAPI real-time endpoint
  -> Kafka weather_snapshots topic
  -> Prometheus metrics
  -> Grafana KPIs
```

## Tool Justification

- Airflow: makes the pipeline robust through scheduling, retries, visible task dependencies, and logs.
- Kafka: captures real-time product and weather events without coupling user requests directly to downstream analytics.
- Spark: provides scalable batch feature generation from Parquet snapshots for future ranking and ML work.
- dbt: makes SQL marts testable, documented, and portable between Postgres and Snowflake.
- Snowflake: gives the project a credible cloud analytics warehouse target beyond local Postgres.
- Terraform: makes warehouse/cloud infrastructure reproducible instead of manually configured.
- Prometheus: measures API reliability, latency, Kafka publish health, weather usage, and itinerary generation.
- Grafana: turns Prometheus metrics into dashboards that show operational health and product KPIs.

## Local Commands

Initialize Airflow on the first run:

```bash
docker compose up --build airflow-init
```

Start the full platform:

```bash
docker compose up --build
```

Airflow UI:

```text
http://localhost:8088
username: admin
password: admin
```

Trigger or monitor:

```text
holiday_itinerary_pipeline
```

Run dbt manually:

```bash
docker compose exec dbt dbt run --profiles-dir .
docker compose exec dbt dbt test --profiles-dir .
```

Prometheus:

```text
http://localhost:9090
```

Grafana:

```text
http://localhost:3000
username: admin
password: admin
```

Kafka UI:

```text
http://localhost:8090
```

Spark UI:

```text
http://localhost:8080
```

Local Spark resource defaults:

```env
SPARK_WORKER_CORES=2
SPARK_WORKER_MEMORY=2G
SPARK_DRIVER_MEMORY=1g
SPARK_EXECUTOR_MEMORY=1g
SPARK_EXECUTOR_CORES=1
SPARK_SQL_SHUFFLE_PARTITIONS=8
```

Increase these only if Docker Desktop has enough CPU/RAM allocated.

## Current KPI Coverage

FastAPI exposes:

```text
GET /metrics
```

Current metrics:

- API request volume by method, path, and status
- API latency by path
- generated itinerary count by city
- selected itinerary place count by city
- weather request count by city and status
- Kafka publish success/failure count by topic
- itinerary category match rate by city
- average distance between consecutive itinerary stops
- average graph recommendation count per selected place
- weather suitability score for the selected itinerary mix

Grafana includes a provisioned `Holiday Platform KPIs` dashboard for these metrics.

## Next Improvements

1. Add weather-aware itinerary ranking so rain, wind, or temperature influence indoor/outdoor POI selection.
2. Persist Kafka events to Postgres or Snowflake for historical product analytics.
3. Add a Kafka consumer or Spark streaming job for weather/event aggregation.
4. Add dbt models for itinerary event analytics and weather-aware recommendation quality.
5. Extend Terraform beyond Snowflake to provision managed Kafka, object storage, secrets, and Spark infrastructure.
6. Add model-quality KPIs such as itinerary acceptance rate, category match rate, average distance between stops, and graph recommendation click rate.
