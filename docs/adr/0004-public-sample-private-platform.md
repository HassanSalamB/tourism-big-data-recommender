---
status: accepted
---

# Separate the public sample from the private data platform

Render hosts a lightweight Streamlit Portfolio Sample, while PostgreSQL, Neo4j, Kafka, Spark, Airflow, dbt, Prometheus, Grafana, and backups run on the private Proxmox target. This keeps the product accessible without exposing administrative interfaces or paying to keep the entire stateful demonstration running publicly.

## Consequences

The portfolio must label recorded screenshots as Recorded Evidence, show backend links only after live verification, and degrade to the curated sample when the private platform is unavailable.
