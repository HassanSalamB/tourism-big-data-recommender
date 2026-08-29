# Product and Data Platform Roadmap

The roadmap prioritizes user value and trust before additional infrastructure. Existing modules should pass the deletion test: each one must support a visible capability, operational property, or evaluation question.

## Current baseline

Implemented today:

- DATAtourisme archive retrieval and content-hash change detection.
- Bronze JSONB, normalized Silver relations, Parquet snapshots, and Gold H3 summaries.
- Ordered Airflow DAG with Spark feature computation, Neo4j synchronization, and dbt tests.
- FastAPI and Streamlit itinerary product.
- Kafka weather/itinerary events plus an idempotent PostgreSQL analytics consumer.
- Prometheus product-quality metrics, Grafana dashboards, and Alertmanager rules.
- Public Render Portfolio Sample and a hardened Proxmox release definition.

## Priority 1 — recommendation quality

1. Replace fixed demonstration times with opening-hours validation and configurable visit duration.
2. Add a real travel-time matrix for walking, transit, or driving instead of treating coordinate distance as a route.
3. Turn weather from an after-the-fact metric into a transparent planning signal that can prefer indoor places during adverse conditions.
4. Let users lock, remove, reorder, and regenerate individual stops without rebuilding the entire Itinerary.
5. Add a scoring explanation for each selected place: Interest match, proximity, opening-hours fit, diversity, weather, and graph context.

## Priority 2 — measurable evaluation

1. Create repeatable evaluation personas: family, culture weekend, outdoor traveller, and accessibility-sensitive traveller.
2. Measure Interest coverage, empty-day rate, duplicate category concentration, total travel time, opening-hours violations, and user edits.
3. Add offline comparison between the geographic baseline and future ranking approaches.
4. Store accepted, removed, reordered, and regenerated stops as explicit feedback events.
5. Establish target thresholds before describing a ranking model as an improvement.

## Priority 3 — data trust and lineage

1. Expose source snapshot, ingestion time, normalization version, and graph synchronization version for each served place.
2. Add a quarantine interface for malformed coordinates, missing identity, and unexpected taxonomy changes.
3. Add dbt freshness checks and pipeline service-level indicators for Source Snapshot age and Trusted Place availability.
4. Move archives and Parquet snapshots to versioned object storage when the Proxmox deployment outgrows local volumes.
5. Add contract tests using a small versioned DATAtourisme fixture.

## Priority 4 — operational maturity

1. Run and document a restore exercise; measure recovery time and recovery point instead of treating targets as proven.
2. Add authenticated access policies for every private administrative interface.
3. Add Kafka retry/dead-letter handling and consumer-lag alerting.
4. Add separate liveness, readiness, and dependency-health interfaces.
5. Add image vulnerability scanning and software-bill-of-material generation to CI.

## Priority 5 — scale only when measured

1. Benchmark Pandas and Spark with increasing snapshot sizes and publish the crossover point.
2. Partition or incrementally rebuild Parquet features instead of rewriting complete snapshots.
3. Introduce Kubernetes only when modules need independent scaling, multi-host resilience, or managed rollout behavior.
4. Use Snowflake only when shared cloud analytics, concurrency, or external BI consumption justifies the additional platform.

## Best portfolio story

The strongest next demonstration is not another technology logo. It is an itinerary a user can inspect and edit, backed by visible data lineage and a measured quality comparison against the current geographic baseline.
