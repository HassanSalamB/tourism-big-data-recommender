# Holiday Itinerary Interview Guide

This guide explains how to present the project as a data product, defend its engineering choices, and remain precise about recommendation quality, deployment state, and personal ownership.

## The story in one sentence

I built and evolved a tourism data platform that incrementally transforms DATAtourisme snapshots into trusted place data, explainable itineraries, graph relationships, analytical features, product events, and observable platform evidence.

## 30-second answer

> Holiday Itinerary is an end-to-end tourism data product. Airflow orchestrates content-aware ingestion from DATAtourisme into Bronze, Silver, and Gold data; Spark creates city features, dbt builds tested marts, and Neo4j stores POI relationships. FastAPI plans multi-day itineraries from trusted places using Interest filtering and geographic grouping, while Streamlit provides the user experience. Kafka captures itinerary and weather events, and Prometheus, Grafana, and Alertmanager expose reliability and quality signals. The public Render version uses a clearly labelled Paris sample, while the full stateful platform is designed for the private Proxmox environment.

## Two-minute architecture walkthrough

1. **Source acquisition:** Airflow retrieves a DATAtourisme archive and records source metadata.
2. **Incremental Bronze:** SHA-256 content hashes distinguish new, changed, and unchanged Point of Interest payloads before raw JSONB is stored in PostgreSQL.
3. **Trusted Silver:** Pandas processes irregular nested JSON in chunks, validates identity and coordinates, and builds relational places, categories, place-category links, prices, and timings. It also writes a Parquet snapshot.
4. **Decision outputs:** Spark computes city features from Parquet, the Gold module builds H3 spatial summaries, Neo4j synchronizes POI/City/Category relationships, and dbt creates tested analytical marts.
5. **Request serving:** Streamlit sends Destination, duration, pace, and Interests to FastAPI. Candidate Places are filtered by Interest before KMeans forms geographic Day Plans.
6. **Enrichment:** Neo4j adds Related Places and Open-Meteo supplies current weather context. These enrich the response without becoming hidden sources of truth.
7. **Events and feedback:** Kafka receives weather and itinerary events. An idempotent consumer stores event payloads in PostgreSQL using topic, partition, and offset as the uniqueness contract.
8. **Operations:** Prometheus measures request health and planning-quality signals, Grafana visualizes them, and Alertmanager evaluates failure rules.

Use [the architecture diagrams](ARCHITECTURE.md) while giving this explanation.

## What problem does it solve?

Tourism data is fragmented, nested, inconsistently categorized, and not directly usable for planning. The platform creates a governed path from source snapshots to identifiable, filterable places and then produces a multi-day plan that a traveller or reviewer can inspect.

The current product is a planning baseline and engineering prototype. A commercial travel product would need opening-hours accuracy, travel-time routing, inventory/availability, user feedback, and stronger recommendation evaluation.

## What was my contribution?

Use an answer like this and adjust it to the specific interview:

> The repository began from a collaborative educational project and retains the original license and contributor history. My Git history shows the later end-to-end platform integration, ingestion refactoring, dashboard/API and CI work, Airflow/Kafka/Spark/dbt/observability integration, Render portfolio, Proxmox release hardening, architecture work, and the recent product refinements. The initial itinerary clustering implementation has another contributor in Git history, so I distinguish the original algorithm from the platform and product work I added around it.

Do not describe every original Bronze, Silver, Gold, or clustering line as solely authored by you. Git history is the source of truth.

## Why these technologies?

### Why Airflow?

> The pipeline has an ordered dependency chain, retries, and operational state that should be visible. Airflow is the single scheduler, so download, change detection, normalization, Spark, Gold, graph, and dbt execution do not develop separate hidden schedules.

### Why PostgreSQL for Bronze and Silver?

> JSONB preserves replayable source payloads while relational Silver tables support quality rules and request-time queries. For a one-machine portfolio, keeping both trust levels in PostgreSQL reduces operational cost. At larger scale, I would move immutable archives and Parquet to object storage without changing the Trusted Place interface.

### Why Pandas and Spark?

> Pandas handles irregular nested JSON precisely during normalization. Spark operates after Silver, where the schema is stable and feature aggregation can scale. I do not claim Spark is necessary for the current sample size; its value must be demonstrated with benchmarked dataset sizes.

### Why dbt as well as Spark?

> They solve different problems. Spark computes scalable features over Parquet. dbt owns SQL transformations, source contracts, documentation, and tests for analytical marts. Airflow runs them in one defined order, so they are complementary rather than competing schedulers.

### Why H3?

> H3 gives consistent spatial cells for density, coverage, and destination-area analysis. Gold H3 clusters are analytical summaries; they are not the place records returned to travellers.

### Why Neo4j?

> POI, City, and Category relationships are naturally traversable. The current Related Place query is explainable: places are connected through shared categories within a Destination. If the product only required category joins, PostgreSQL would be simpler and Neo4j should be removed.

### Why Kafka?

> Itinerary and weather interactions are event-shaped and should not make the user request depend on downstream analytics. Kafka decouples publication from the idempotent consumer and creates replayable product evidence. For low traffic, a database outbox would be a reasonable simpler alternative.

### Why FastAPI and Streamlit?

> FastAPI provides typed contracts and isolates the product from storage details. Streamlit provides a fast, inspectable portfolio interface. A consumer product with complex collaborative editing might later use a dedicated web frontend, while preserving the FastAPI interface.

## Is this an AI recommendation engine?

> Not currently. It is an explainable deterministic planning baseline. Interests filter eligible places, KMeans creates geographic Day Plans, distance to each cluster centre influences selection, and Neo4j adds category-related context. Calling it AI personalization would be misleading because no model learns from user outcomes.

This answer is a strength: it shows you know the difference between clustering, heuristics, graph relationships, and learned ranking.

## Why KMeans?

> KMeans is a simple baseline for grouping nearby coordinates into the requested number of days. It is deterministic with a fixed seed and easy to inspect. It does not understand roads, transit, opening hours, or attraction duration, so I would compare it with travel-time clustering and route optimization before using it commercially.

## Why apply Interests before KMeans?

> Geographic groups should be formed from places actually eligible for the traveller. Clustering the entire city and filtering afterward can leave empty days or poor group shapes. The implementation now filters Candidate Places first and then chooses up to the number of available candidates as geographic day groups.

## How does incremental ingestion work?

> The source archive is checked for change, and each Point of Interest has a canonical content hash. Unchanged records are not rewritten. Silver and downstream synchronization fields track which records require further work. This reduces unnecessary processing while preserving raw replay capability.

## What are Bronze, Silver, and Gold here?

- **Bronze:** source-aligned raw JSONB plus content identity.
- **Silver:** normalized Trusted Places, categories, timings, prices, and links.
- **Gold:** decision-oriented H3 summaries, features, graphs, and analytical marts.

Strong answer:

> The names matter less than their contracts. Bronze preserves what arrived, Silver defines what the product can trust, and Gold shapes that trusted data for a specific decision or analysis.

## How is itinerary quality measured?

Current signals include:

- Interest/category match rate.
- Average distance between consecutive stops.
- Average graph-enrichment count.
- Weather suitability of the selected mix.
- Generated-itinerary and selected-place counts.

Honest answer:

> These are diagnostic signals, not proof of user satisfaction. The next evaluation layer should record accepted, removed, reordered, and regenerated stops and compare the current geographic baseline with alternative ranking approaches on repeatable traveller personas.

## Does weather change the itinerary?

> Not yet. Open-Meteo provides current context and weather-suitability measurement. The planner does not currently rescore or reorder stops from the weather result. A future version should make that influence explicit and explain why an indoor place was preferred.

## Does it respect opening hours and travel time?

> No. The current time windows are demonstration slots, and geographic coordinate distance is not road or transit travel time. Production planning needs normalized opening hours, timezone handling, duration, a routing matrix, and constraint validation.

## What is live on Render?

> The Streamlit portfolio interface is public and uses a curated Paris Portfolio Sample. Engineering panels show Recorded Evidence from verified full-stack runs. They do not claim Airflow, Kafka, Spark, Neo4j, or Grafana are currently running on Render.

## Why Proxmox?

> The full platform contains stateful and continuously running modules that are expensive and awkward to host as many public PaaS services. Proxmox provides a private, controllable environment for Docker, volumes, monitoring, and backups. Administrative interfaces should remain behind authenticated Cloudflare access rather than being exposed directly.

## How would you productionize it?

1. Define the target traveller segment and measurable planning outcome.
2. Version Source Snapshots, transformation code, taxonomy mappings, and served data together.
3. Add opening-hours, timezone, accessibility, visit-duration, and travel-time contracts.
4. Build an explicit planner interface with a baseline adapter and future ranking/optimization adapters.
5. Store user edits and acceptance events with consent and retention rules.
6. Evaluate offline on repeatable personas, then conduct controlled online experiments.
7. Add authentication, authorization, audit logging, encryption, and data-retention policies.
8. Use an object store for immutable archives/Parquet and managed stateful systems when scale justifies them.
9. Run backup/restore exercises and define measured service-level objectives.
10. Monitor source freshness, data-quality failures, planning latency, drift, and user outcomes.

## How would you scale it?

> I would measure each stage first. Archive and Parquet data would move to object storage. Bronze/Silver processing would become partitioned by Source Snapshot or changed-record window. Spark would be sized from benchmark evidence. FastAPI and Streamlit are stateless enough to replicate, while PostgreSQL, Neo4j, Kafka, and Airflow need explicit state and recovery strategies. Kubernetes becomes justified only when those modules need independent scaling or multi-host resilience.

## How do you handle failures?

> Airflow owns task retries and exposes failed stages. Content hashes and downstream synchronization timestamps make reruns repeatable. Kafka publication failures are counted without failing the traveller request, and the consumer uses topic/partition/offset uniqueness to avoid duplicate event rows. The public portfolio falls back to the curated sample and Recorded Evidence when the private backend is unavailable.

## What would you monitor?

- Source Snapshot age and download success.
- New, changed, unchanged, and quarantined record counts.
- Airflow task duration, retry count, and last successful DAG run.
- Silver quality-rule failures and available Trusted Place count.
- Spark/dbt duration and test results.
- FastAPI latency and error rate by route.
- Kafka publication failures, consumer lag, and latest event age.
- Interest match, empty-day rate, travel distance/time, and user edits.
- Database health, volume capacity, backup age, and restore-test age.

## Security answer

> Runtime secrets are excluded from Git, the release definition requires environment-driven credentials, administrative ports bind to loopback, and Cloudflare Tunnel is the intended ingress. Before handling user profiles, I would add identity, role-based authorization, audit logs, secret management, encryption, retention controls, and a threat model. Local default credentials are development convenience, not a production security claim.

## CI/CD answer

> CI compiles the Python code, validates development and release Compose contracts, runs repository tests, and builds both application images. On pushes it publishes immutable SHA-tagged images to GHCR. The release configuration is tested for loopback binding, resource limits, versioned images, and environment-driven credentials. Deployment remains a separate, explicit Proxmox operation.

## Difficult questions

### “Is this overengineered?”

> For four public sample records, absolutely. The public sample is only the accessible interface. The full platform demonstrates specific data-engineering patterns, but every module still has to pass a deletion test. Spark requires scale evidence, Neo4j requires a graph query, and Kafka requires replayable asynchronous events; otherwise a smaller PostgreSQL/FastAPI product is better.

### “Why not use one Python script?”

> A script is appropriate for exploration. This project also demonstrates incremental state, stage retries, replay, separate trust contracts, request serving, events, and operational evidence. The command-line pipeline still exists for development, while Airflow owns scheduled orchestration.

### “Why isn’t the recommendation personalized?”

> There is no trustworthy user-outcome dataset yet. I prefer an explainable baseline and explicit limitations over training a model on invented feedback. The event path is designed to collect the future evidence needed for personalization.

### “Why use Spark on a small dataset?”

> It is a scale-path demonstration, not a current performance necessity. The roadmap explicitly requires a Pandas-versus-Spark benchmark and a published crossover point. If Spark does not win at the expected scale, it should be removed.

### “Why use Neo4j instead of SQL?”

> Shared-category relationships can be expressed in SQL. Neo4j earns its place only if traversal and relationship-driven exploration remain a visible product capability. The architecture does not treat the technology choice as permanent by default.

### “Can you sell this?”

> I would offer a tailored proof of concept to a tourism board, destination platform, travel-tech company, or hospitality consultancy. The current project proves the data-product workflow. A sellable product needs target-user validation, reliable inventory/opening-hours data, routing, feedback evaluation, and operational support.

### “What would you change first?”

> I would replace fixed times and coordinate-distance assumptions with opening-hours and travel-time constraints, then add interactive itinerary editing and measure the changes users make. That improves actual traveller value more than adding another infrastructure technology.

## STAR examples

### Making the public demo honest

- **Situation:** The hosted interface needed to remain available even when the full private platform was offline.
- **Task:** Avoid presenting sample destination records or old screenshots as live backend coverage.
- **Action:** I created explicit Portfolio Sample, Recorded Evidence, Live Backend, and maintenance states, restricted the sample to declared Paris data, and enabled backend links only when configured and verified.
- **Result:** Reviewers can use the product while clearly understanding which evidence is live, recorded, or sampled.

### Hardening the deployment path

- **Situation:** Development Compose exposed convenient defaults and did not represent a safe persistent host.
- **Task:** Prepare a reproducible Proxmox release without claiming it was already deployed.
- **Action:** I added versioned images, loopback-bound interfaces, environment-driven credentials, resource/log limits, Cloudflare Tunnel integration, health checks, backup scripts, and repository tests for those contracts.
- **Result:** The repository has a credible deployment path whose security properties can be inspected before activation.

### Integrating the platform

- **Situation:** Individual ETL, API, and dashboard modules did not yet tell one complete data-product story.
- **Task:** Connect ingestion, processing, serving, events, and observability.
- **Action:** I integrated Airflow, Spark, dbt, Kafka analytics, Prometheus/Grafana, the Render portfolio, service registry, architecture evidence, and CI around the existing domain modules.
- **Result:** The project now demonstrates both how data becomes an Itinerary and how that product is operated and evaluated.

## Five-minute demo script

1. Open **Project Home** and explain Portfolio Sample versus Recorded Evidence.
2. Open **Itinerary App**, select Paris, days, pace, and Interests, then generate a plan.
3. Explain that Interests are applied before geographic grouping and that time slots are currently demonstrative.
4. Open **Architecture Details** and trace a Source Snapshot through Bronze, Silver, Spark/Gold/Neo4j/dbt.
5. Open **Pipeline & Storage** and show the recorded Airflow, Spark, PostgreSQL, and dbt evidence.
6. Open **Serving & Graph** and trace Streamlit → FastAPI → Trusted Places → KMeans → Neo4j → Kafka.
7. Open **Observability** and explain the difference between platform health metrics and itinerary-quality signals.
8. Finish with the next product step: editable plans, opening-hours/travel-time constraints, and measured user feedback.

## Questions to ask the interviewer

- How does your team evaluate recommendation usefulness before online experimentation?
- Which source-data quality failures cause the most operational pain?
- How do you represent opening hours, availability, and timezone changes?
- Does the team own both pipelines and user-facing recommendation interfaces?
- What feedback signals are available after a traveller edits or books a plan?
- When does your organization choose Spark over warehouse SQL or Pandas?

## Final presentation rules

1. Say **Portfolio Sample**, not “full live data.”
2. Say **Recorded Evidence**, not “live Airflow” unless it is reachable and verified.
3. Say **geographic planning baseline**, not “AI recommendation engine.”
4. Say **current weather context**, not “trip forecast.”
5. Distinguish coordinate grouping from route optimization.
6. Distinguish your commits from the original collaborative implementation.
7. Lead with traveller and data-trust problems; use the technology stack as evidence.
