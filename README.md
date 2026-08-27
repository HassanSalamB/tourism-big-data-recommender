# Holiday Itinerary Data Platform

**[Open the public Holiday Itinerary Data Platform](https://holiday-itinerary-platform.onrender.com/)**

The public Streamlit portfolio presents the original itinerary experience and recorded execution evidence from Airflow, Kafka, Spark, Postgres, Neo4j, FastAPI, Prometheus, and Grafana. The public service uses a clearly labelled curated sample; the complete data platform remains reproducible through Docker Compose.

This project builds a local ETL pipeline for DATAtourisme data. It ingests raw POI JSON into Postgres bronze tables, cleans and normalizes the data into silver tables with pandas chunks, then builds gold outputs for itinerary exploration in Postgres and Neo4j.
It runs as an integrated data-platform stack with Airflow, Kafka, Spark, dbt, Prometheus, Grafana, FastAPI, and Streamlit.

## What The Pipeline Does

```text
DATAtourisme ZIP feed
  -> Airflow orchestration
  -> Bronze ZIP download
  -> Bronze content-hash change detection
  -> Bronze Postgres JSONB table
  -> Silver cleaned relational tables + Parquet snapshot
  -> Spark city feature generation
  -> Gold Postgres H3 clusters
  -> dbt analytics marts and tests
  -> Gold Neo4j POI graph
  -> FastAPI + Streamlit itinerary app
  -> Prometheus + Grafana observability
```

The live itinerary generator currently uses cleaned `silver_places` rows and runtime KMeans clustering. The precomputed `gold_clusters` table is an H3-based summary layer used for analytics/dashboard counts, not the direct source of itinerary stops.

The reusable pipeline entrypoint is:

```bash
python3 -m src.pipeline --silver-full
```

When running with Docker Compose, Airflow is the main orchestrator. It runs the pipeline DAG in series: ZIP download, bronze change detection/load, silver, Spark features, gold Postgres, Neo4j, and dbt tests.

## Requirements

You need:

- Docker Desktop, recommended for the full project
- A `.env` file with DATAtourisme, Postgres, Neo4j, Kafka, Airflow, and Snowflake settings
- Enough disk space for the DATAtourisme ZIP in `data/raw/`

The project already installs Python dependencies inside the Docker image from `requirements.txt`. Field extraction rules for silver live in `config.yaml` under `silver_extraction.text_field_paths` and `silver_extraction.numeric_field_paths`, so common DATAtourisme path changes do not require editing Python code.

## Environment Variables

Create or update `.env` in the project root:

```env
DATATOURISME_TOKEN=your_api_key/your_feed_id

DB_USER=admin
DB_PASSWORD=root
DB_NAME=holiday_db
DB_PORT=5432
DB_HOST=postgres

NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword
NEO4J_URI=bolt://neo4j:7687
NEO4J_HOST=neo4j
NEO4J_PORT=7687

KAFKA_BOOTSTRAP_SERVERS=kafka:9092
AIRFLOW_UID=50000

SPARK_WORKER_CORES=2
SPARK_WORKER_MEMORY=2G
SPARK_DRIVER_MEMORY=1g
SPARK_EXECUTOR_MEMORY=1g
SPARK_EXECUTOR_CORES=1
SPARK_SQL_SHUFFLE_PARTITIONS=8
```

Notes:

- `DATATOURISME_TOKEN` is used to download the ZIP feed from `https://diffuseur.datatourisme.fr/webservice/`.
- In Docker, `DB_HOST=postgres` and `NEO4J_URI=bolt://neo4j:7687` are correct because services talk through the Compose network.
- In Docker, `KAFKA_BOOTSTRAP_SERVERS=kafka:9092` is correct for API event publishing.
- From your host browser, use `localhost` ports instead.

## Run With Docker

Initialize Airflow metadata and admin user if this is the first run:

```bash
docker compose up --build airflow-init
```

Start the full stack:

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

Open Airflow and trigger or monitor the `holiday_itinerary_pipeline` DAG:

```text
http://localhost:8088
username: admin
password: admin
```

Follow Airflow scheduler logs:

```bash
docker compose logs -f airflow-scheduler
```

To see DATAtourisme download progress, open the Airflow task logs for:

```text
holiday_itinerary_pipeline -> bronze_download_zip
```

To see key/content-hash comparison counts, open:

```text
holiday_itinerary_pipeline -> bronze_detect_and_load_changes
```

Generate an itinerary through the API after silver data is loaded:

```bash
curl -X POST http://localhost:8000/generate-itinerary \
  -H "Content-Type: application/json" \
  -d '{"city": "Paris", "days": 3, "max_places_per_day": 5, "categories": ["Beach", "Museum"]}'
```

Run dbt manually if needed:

```bash
docker compose exec dbt dbt run --profiles-dir .
```

```bash
docker compose exec dbt dbt test --profiles-dir .
```

## CI/CD With GitHub Actions

The repository includes a GitHub Actions workflow at:

```text
.github/workflows/ci-cd.yml
```

On pull requests and pushes to `dev` or `main`, it runs:

- Python syntax checks for `src/`
- Docker Compose config validation
- Docker image build validation

On pushes to `dev` or `main`, it can also publish the Docker image to Docker Hub if these GitHub repository secrets are configured:

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

The published image tags are:

```text
DOCKERHUB_USERNAME/holiday-itinerary:dev
DOCKERHUB_USERNAME/holiday-itinerary:main
DOCKERHUB_USERNAME/holiday-itinerary:<git-sha>
```

Docker Hub stores the built image. It does not host or run the dashboard. To make the app visible to users, a server still needs to pull the image and run the containers.

## Web UIs And Ports

FastAPI itinerary service:

```text
http://localhost:8000/docs
```

Streamlit dashboard:

```text
http://localhost:8501
```

Airflow:

```text
http://localhost:8088
```

Prometheus:

```text
http://localhost:9090
```

Kafka UI:

```text
http://localhost:8090
```

Grafana:

```text
http://localhost:3000
username: admin
password: admin
```

Spark UI:

```text
http://localhost:8080
```

Adminer for Postgres:

```text
http://localhost:5050
```

Use:

```text
System: PostgreSQL
Server: postgres
Username: admin
Password: root
Database: holiday_db
```

Neo4j Browser:

```text
http://localhost:7474
```

Use:

```text
Username: neo4j
Password: neo4jpassword
Connect URL in browser: bolt://localhost:7687
```

Inside Docker, the Python app connects to Neo4j with:

```text
bolt://neo4j:7687
```

Do not type `bolt://...` into Chrome as a web page. `bolt://` is a database driver protocol, while the browser UI is `http://localhost:7474`.

## App Serving Flow

The Streamlit dashboard does not query Postgres or Neo4j directly. It calls FastAPI over HTTP:

```text
Streamlit dashboard
  -> FastAPI JSON endpoints
  -> Postgres silver/gold tables
  -> Neo4j recommendations
  -> Open-Meteo weather
  -> Kafka event publishing
  -> Prometheus metrics
```

Main API endpoints:

```text
GET  /health
GET  /summary
GET  /cities
GET  /categories
GET  /places
GET  /weather/current?city=Paris
GET  /metrics
POST /generate-itinerary
```

`/generate-itinerary` works like this:

- reads cleaned POIs for the selected city from `silver_places`
- runs KMeans on latitude/longitude to split the city into day-sized geographic groups
- treats selected dashboard interests/categories as preferences, not hard filters
- fills each day with nearby POIs so one interest such as Beach does not make every stop a beach
- asks Neo4j for related POI suggestions for the selected itinerary stops
- publishes an `itinerary.generated` event to Kafka
- increments Prometheus itinerary metrics

The Streamlit map is based on `silver_places.lat` and `silver_places.lon` returned by FastAPI. Neo4j powers related-place suggestions, not the geographic map.

The weather endpoint publishes weather snapshot events to Kafka and increments Prometheus weather metrics.

## Fresh Rebuild

If you want to rebuild from a clean database state, remove the Docker volumes and start again:

```bash
docker compose down -v
```

```bash
docker compose up --build
```

This is useful after changing silver cleaning logic, because silver normally skips bronze rows whose raw `content_hash` did not change.

## Pipeline Stages

### Bronze: `src/bronze/bronze_loader.py` + `src/bronze/data_api.py`

Bronze is split into two steps:

- `src/bronze/data_api.py`: API call + ZIP/metadata caching
- `src/bronze/bronze_loader.py`: ZIP parsing + Postgres bronze upsert

The pipeline calls them in sequence: fetch first, then load.

Raw POI JSON is stored in Postgres:

```text
bronze_raw_poi
```

Important columns:

- `id`: raw DATAtourisme `@id`
- `source_identifier`: raw `dc:identifier`
- `raw_payload`: original JSONB document
- `source_file`: ZIP entry name
- `content_hash`: SHA-256 hash of the raw JSON payload
- `created_at`: first time the row was inserted
- `updated_at`: last time the raw content changed
- `ingested_at`: last time this row was ingested/updated

Bronze compares incoming ZIP documents with existing Postgres hashes. If the hash is unchanged, it skips rewriting that POI.

Bronze also stores ZIP download metadata in:

```text
data/raw/datatourisme_download.zip.metadata.json
```

If `token_filename` is unchanged and bronze was already loaded for that filename, bronze skips reloading raw rows and the pipeline skips silver/gold.

### Silver: `src/silver/data_normalizer.py`

Silver reads changed bronze rows and cleans them in pandas chunks.

Main table:

```text
silver_places
```

Supporting tables:

```text
silver_categories
silver_place_categories
silver_timings
silver_prices
```

Silver cleaning includes:

- mapping nested DATAtourisme JSON paths from `config.yaml` into flat silver columns
- keeping repeated text/numeric path strings in `config.yaml`, not inside Python
- extracting French text with English fallback
- description fallback from `dc:description`, `shortDescription`, and `rdfs:comment`
- trimming empty strings to null
- converting coordinates and prices to numeric values
- rejecting rows without `id`, `name`, `lat`, or `lon`
- rejecting invalid coordinate ranges
- exploding and deduplicating category lists
- parsing timing fields into date/time values
- deduplicating price and timing rows

Silver compares:

```text
bronze_raw_poi.content_hash
silver_places.source_content_hash
```

If the hash is the same, silver skips that row. If you change cleaning logic and want all rows reprocessed, do a fresh rebuild.

### Gold Postgres: `src/gold/postgres_warehouse.py`

Gold Postgres trusts the cleaned silver layer. It does not perform the silver cleaning again.

It builds:

```text
gold_clusters
```

Gold Postgres:

- reads cleaned `silver_places`
- groups POIs into H3 cells
- calculates a simple category score
- writes cluster summaries
- prints a small sample itinerary from the highest-ranked city clusters

### Gold Neo4j: `src/gold/neo4j_graph_loader.py`

Neo4j loads changed silver POIs into a graph:

```text
(:POI)-[:LOCATED_IN]->(:City)
(:POI)-[:HAS_CATEGORY]->(:Category)
```

It uses `neo4j_synced_at` to skip rows already synced after the latest silver update.

## Sync Columns

In `silver_places`:

- `created_at`: when the silver row was first created
- `updated_at`: when silver last updated the cleaned row
- `neo4j_synced_at`: when Neo4j last loaded the row
- `gold_pg_synced_at`: when Postgres gold last used the row
- `source_content_hash`: the bronze hash that produced the silver row

Downstream stages compare `updated_at` with their own sync timestamp:

```sql
neo4j_synced_at IS NULL OR updated_at > neo4j_synced_at
```

```sql
gold_pg_synced_at IS NULL OR updated_at > gold_pg_synced_at
```

## Project Structure

```text
.
├── README.md
├── ARCHITECTURE_AND_DECISIONS.md
├── config.yaml
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.airflow
├── requirements.txt
├── requirements-analytics.txt
├── architecture.mmd
├── airflow/
├── dbt/
├── monitoring/
├── terraform/
├── data/
│   ├── raw/
│   └── silver/parquet/
└── src/
    ├── pipeline.py
    ├── bronze/
    │   ├── bronze_loader.py
    │   └── data_api.py
    ├── silver/
    │   └── data_normalizer.py
    ├── spark/
    │   └── city_feature_job.py
    ├── gold/
    │   ├── postgres_warehouse.py
    │   └── neo4j_graph_loader.py
    ├── streaming/
    │   └── kafka_events.py
    ├── api/
    │   ├── app.py
    │   └── dashboard.py
    └── utils/
        ├── config.py
        └── connections.py
```

## Useful Commands

Compile-check Python files inside Docker:

```bash
docker compose run --rm --no-deps api python3 -m py_compile src/pipeline.py src/bronze/bronze_loader.py src/bronze/data_api.py src/silver/data_normalizer.py src/spark/city_feature_job.py src/gold/postgres_warehouse.py src/gold/neo4j_graph_loader.py src/streaming/kafka_events.py src/api/app.py src/api/dashboard.py src/utils/config.py src/utils/connections.py
```

Open a shell in the API container:

```bash
docker compose run --rm api bash
```

Stop services:

```bash
docker compose down
```
