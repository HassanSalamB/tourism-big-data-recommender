# Architecture And Decisions

This document explains the current ETL architecture and the main design decisions behind it.

## Project Goal

The project prepares DATAtourisme data for an itinerary application. The app should eventually support questions such as:

- where a user wants to visit
- what type of POIs they prefer
- when they want to visit
- what budget range they care about
- which nearby/related POIs are useful for itinerary planning

## Current Architecture

```text
DATAtourisme feed
  -> Bronze Postgres JSONB
  -> Silver Postgres relational tables cleaned with pandas chunks
  -> Gold Postgres clusters
  -> Neo4j POI graph
  -> FastAPI service
  -> Streamlit dashboard
```

The current pipeline entrypoint is:

```text
src/pipeline.py
```

## Bronze Layer

File:

```text
src/bronze/bronze_loader.py
src/bronze/data_api.py
```

Primary tables:

```text
bronze_raw_poi
```

Bronze responsibilities:

- download the DATAtourisme ZIP feed
- stream ZIP JSON entries instead of loading the full archive into memory
- store the raw JSON payload in Postgres `JSONB`
- compute a stable SHA-256 `content_hash` for each POI
- insert new rows and update only changed rows
- skip unchanged POIs

Why Postgres JSONB for bronze:

- DATAtourisme payloads are nested and irregular
- the raw payload remains replayable for future silver rebuilds
- bronze, silver, and gold stay in the same database engine
- hash comparisons can happen close to the data
- this avoids running MongoDB for this project

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

- read only changed bronze rows by comparing hashes
- map nested fields with declarative path maps stored in `config.yaml`
- clean data with pandas chunk operations
- normalize one raw POI into relational tables
- write a portable Parquet snapshot
- keep downstream sync timestamps for gold and Neo4j

Silver cleaning rules include:

- load `silver_extraction.text_field_paths` and `silver_extraction.numeric_field_paths` from `config.yaml`
- keep repeated DATAtourisme path strings outside Python so path tweaks are config-only
- keep French text first, English as fallback
- use `dc:description`, `shortDescription`, and `rdfs:comment` for descriptions
- trim text values and convert empty strings to null
- convert latitude/longitude to numeric columns
- reject invalid latitude/longitude ranges
- reject rows missing `id`, `name`, `lat`, or `lon`
- explode category lists into bridge rows
- deduplicate category, timing, and price rows
- parse timing values into dates/times
- convert price values to numeric values

Important decision:

Silver skips unchanged bronze rows using:

```text
bronze_raw_poi.content_hash == silver_places.source_content_hash
```

If silver cleaning code changes and the raw bronze hash does not change, run a fresh rebuild if you want old rows reprocessed.

## Gold Postgres Layer

File:

```text
src/gold/postgres_warehouse.py
```

Primary table:

```text
gold_clusters
```

Gold Postgres responsibilities:

- trust the cleaned silver layer
- read silver rows in chunks
- compute H3 cluster IDs
- calculate a simple category-based score
- write cluster summaries for itinerary exploration
- print a sample itinerary from high-ranked clusters

Gold does not repeat silver cleaning rules. For example, it no longer revalidates missing coordinates because that belongs to silver.

Important distinction:

- `gold_clusters` uses H3 grid cells, not KMeans
- `gold_clusters` stores cluster summaries, not full day itineraries
- the live dashboard itinerary currently reads actual POIs from `silver_places`

## Gold Neo4j Layer

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

- create uniqueness constraints for POI, Category, and City nodes
- stream changed silver rows from Postgres
- replace refreshed POI nodes so stale relationships disappear
- mark rows as synced in `silver_places.neo4j_synced_at`

Neo4j is used by the app for related-place suggestions. It is not the source of the Streamlit geographic map.

## FastAPI And Streamlit App Layer

Files:

```text
src/api/app.py
src/api/dashboard.py
```

FastAPI responsibilities:

- expose JSON endpoints for the dashboard
- read dashboard summaries from Postgres
- read city, category, place, and map data from `silver_places` and related silver tables
- run request-time KMeans clustering for itinerary days
- ask Neo4j for related POI suggestions
- return JSON-safe values to Streamlit

Streamlit responsibilities:

- provide the dashboard UI
- call FastAPI with `requests`
- show metrics, city/category exploration, maps, and generated itineraries
- treat selected interests/categories as preferences for itinerary generation

The dashboard and API communicate through HTTP:

```text
Streamlit -> FastAPI -> Postgres / Neo4j
```

Inside Docker Compose, the dashboard reaches the API with:

```text
API_BASE_URL=http://api:8000
```

From the host browser:

```text
FastAPI docs: http://localhost:8000/docs
Streamlit:    http://localhost:8501
```

## Itinerary Generation

The live itinerary flow is separate from `gold_clusters`:

```text
silver_places for selected city
  -> KMeans on lat/lon
  -> one cluster per requested day
  -> nearest POIs to each cluster center
  -> selected interests/categories lightly preferred
  -> Neo4j related suggestions
  -> Streamlit itinerary cards and map
```

KMeans is used because the number of clusters depends on the user request. For example, a 3-day trip creates up to 3 geographic groups, while a 5-day trip creates up to 5.

Selected interests such as Beach, Museum, or Restaurant are preferences, not hard filters. This keeps an itinerary varied: selecting Beach can add beach-related stops, but the planner still fills days with other nearby POIs.

Neo4j does not choose the day clusters. It adds related POI suggestions for places already selected by the Postgres/KMeans flow.

## Incremental Strategy

Bronze tracks source changes with:

```text
bronze_raw_poi.content_hash
```

Silver remembers which raw hash produced each cleaned row with:

```text
silver_places.source_content_hash
```

Gold and Neo4j use timestamps:

```text
silver_places.updated_at
silver_places.gold_pg_synced_at
silver_places.neo4j_synced_at
```

This means:

- bronze skips unchanged raw POIs
- silver skips unchanged bronze POIs
- gold Postgres skips if silver has no changes since the last gold sync
- Neo4j skips if silver has no changes since the last graph sync

## Why Pandas Instead Of PySpark Here

Pandas is used in silver because the current project runs locally/Docker Compose on one machine. It provides familiar DataFrame cleaning without requiring Java or a Spark cluster.

PySpark would be useful later if:

- the data grows far beyond what one machine can handle comfortably
- the project moves to Databricks, EMR, Dataproc, Synapse, Kubernetes, or another real Spark cluster
- the team wants to learn distributed processing explicitly

For now, chunked pandas gives a good balance:

- no Java dependency
- lower setup complexity
- bounded memory use
- clear cleaning operations

## Database Tables

Bronze:

```text
bronze_raw_poi
```

Silver:

```text
silver_places
silver_categories
silver_place_categories
silver_timings
silver_prices
```

Gold Postgres:

```text
gold_clusters
```

Neo4j:

```text
POI nodes
City nodes
Category nodes
LOCATED_IN relationships
HAS_CATEGORY relationships
```

## Service Ports

Postgres:

```text
localhost:5432
```

Adminer:

```text
http://localhost:5050
```

Neo4j Browser:

```text
http://localhost:7474
```

FastAPI:

```text
http://localhost:8000/docs
```

Streamlit:

```text
http://localhost:8501
```

Neo4j Bolt:

```text
bolt://localhost:7687 from the host
bolt://neo4j:7687 from inside Docker
```

## Current Pipeline Files

```text
src/pipeline.py
src/bronze/bronze_loader.py
src/bronze/data_api.py
src/silver/data_normalizer.py
src/gold/postgres_warehouse.py
src/gold/neo4j_graph_loader.py
src/utils/config.py
src/utils/connections.py
src/architecture.mmd
```
