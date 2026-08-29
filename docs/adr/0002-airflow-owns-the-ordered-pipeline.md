---
status: accepted
---

# Let Airflow own the ordered pipeline

Airflow is the single scheduler for download, change detection, normalization, Spark features, Gold synchronization, Neo4j loading, and dbt validation. Spark and dbt remain complementary processing modules inside that order—Spark computes features over trusted Parquet data while dbt owns tested SQL marts—rather than acting as independent schedulers or duplicate transformation paths.

## Consequences

The command-line pipeline remains a stage runner for development, but production scheduling and retry behavior belong to the Airflow DAG.
