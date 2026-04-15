# Holiday Itinerary Data Platform

This project builds a local ETL pipeline for DATAtourisme data. It ingests raw POI JSON into Postgres bronze tables, cleans and normalizes the data into silver tables with pandas chunks, then builds gold outputs for itinerary exploration in Postgres and Neo4j.

## What The Pipeline Does

```text
DATAtourisme ZIP feed
  -> Bronze Postgres JSONB table
  -> Silver cleaned relational tables
  -> Gold Postgres H3 clusters
  -> Gold Neo4j POI graph
```

The main entrypoint is:

```bash
python3 -m src.pipeline --silver-full
```

When running with Docker Compose, the `etl_worker` container runs that command by default.
With current Docker setup, `etl_worker` runs one ETL on startup and then runs it every hour via cron.

## Requirements

You need:

- Docker Desktop, recommended for the full project
- A `.env` file with DATAtourisme, Postgres, and Neo4j settings
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
```

Notes:

- `DATATOURISME_TOKEN` is used to download the ZIP feed from `https://diffuseur.datatourisme.fr/webservice/`.
- In Docker, `DB_HOST=postgres` and `NEO4J_URI=bolt://neo4j:7687` are correct because services talk through the Compose network.
- From your host browser, use `localhost` ports instead.

## Run With Docker

Start the full stack:

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

Follow the ETL worker logs:

```bash
docker compose logs -f etl_worker
```

Check installed cron schedule inside worker:

```bash
docker compose exec etl_worker crontab -l
```

Run only selected stages:

```bash
docker compose run --rm etl_worker python3 -m src.pipeline --skip-api
```

```bash
docker compose run --rm etl_worker python3 -m src.pipeline --skip-neo4j
```

```bash
docker compose run --rm etl_worker python3 -m src.pipeline --skip-api --skip-gold-pg --skip-neo4j --silver-full
```

## Web UIs And Ports

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
├── requirements.txt
├── data/
│   ├── raw/
│   └── silver/parquet/
└── src/
    ├── pipeline.py
    ├── architecture.mmd
    ├── bronze/
    │   ├── bronze_loader.py
    │   └── data_api.py
    ├── silver/
    │   └── data_normalizer.py
    ├── gold/
    │   ├── postgres_warehouse.py
    │   └── neo4j_graph_loader.py
    └── utils/
        ├── config.py
        └── connections.py
```

## Useful Commands

Compile-check Python files inside Docker:

```bash
docker compose run --rm --no-deps etl_worker python3 -m py_compile src/pipeline.py src/bronze/bronze_loader.py src/bronze/data_api.py src/silver/data_normalizer.py src/gold/postgres_warehouse.py src/gold/neo4j_graph_loader.py src/utils/config.py src/utils/connections.py
```

Open a shell in the ETL container:

```bash
docker compose run --rm etl_worker bash
```

Stop services:

```bash
docker compose down
```
