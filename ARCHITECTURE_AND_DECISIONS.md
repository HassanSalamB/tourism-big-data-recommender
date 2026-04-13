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
```

The current pipeline entrypoint is:

```text
src/pipeline.py
```

## Bronze Layer

File:

```text
src/bronze/api_ingest.py
```

Primary tables:

```text
bronze_raw_poi
bronze_feed_state
```

Bronze responsibilities:

- download the DATAtourisme ZIP feed
- optionally probe catalog freshness to avoid unnecessary downloads when the API allows it
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
silver_pipeline_state
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
bronze_feed_state
```

Silver:

```text
silver_places
silver_categories
silver_place_categories
silver_timings
silver_prices
silver_pipeline_state
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

Neo4j Bolt:

```text
bolt://localhost:7687 from the host
bolt://neo4j:7687 from inside Docker
```

## Current Pipeline Files

```text
src/pipeline.py
src/bronze/api_ingest.py
src/silver/data_normalizer.py
src/gold/postgres_warehouse.py
src/gold/neo4j_graph_loader.py
src/utils/config.py
src/utils/connections.py
src/architecture.mmd
```
