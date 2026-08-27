# Accommodation Intelligence Lab

This is a lightweight, reviewer-facing vertical slice of the larger Holiday Itinerary Data Platform. It demonstrates how fragmented accommodation observations can become trusted property records and explainable commercial actions.

The demo is an independent portfolio project. It uses synthetic records and public hospitality concepts and is not affiliated with Lighthouse. It contains no Lighthouse data, code, or confidential information.

## Problems demonstrated

- Multi-source accommodation ingestion with source lineage
- Text and address normalization
- Geographic candidate generation
- Explainable entity-resolution scoring
- Canonical-property survivorship rules
- Required-field and freshness checks
- Rate-parity, demand, and availability signals
- Traceable decision-support recommendations

## Run locally

From the repository root:

```bash
python3 -m venv .venv-demo
source .venv-demo/bin/activate
pip install -r requirements-demo.txt
streamlit run hospitality_demo/app.py
```

Run the pipeline without the UI:

```bash
python3 -m hospitality_demo.pipeline
```

Run the tests:

```bash
python3 -m unittest discover -s tests -p 'test_hospitality_demo.py' -v
```

## Design boundary

The demo intentionally uses deterministic, explainable recommendation rules. The role of the data engineer is to produce a trustworthy facts layer, evidence, and quality controls. A learned model or LLM can be added later, but it should not hide unresolved identities or weak source data.

The complete repository demonstrates the heavier platform path with Airflow, Spark/PySpark, Kafka, dbt, Postgres, Neo4j, FastAPI, Docker, Prometheus, Grafana, Kubernetes, and Terraform.
