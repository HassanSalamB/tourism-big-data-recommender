# Accommodation Intelligence Lab - Engineering Case Study

## Executive summary

This independent portfolio extension demonstrates a hospitality data-engineering problem: turning inconsistent observations from several accommodation providers into a trusted property facts layer that can support analytics, pricing, forecasting, and AI products.

The demo uses synthetic data and public hospitality concepts. It is not affiliated with Lighthouse and contains no Lighthouse code, data, or confidential information.

## The problem

The same accommodation can appear differently across sources:

- names are reordered, shortened, or translated;
- addresses use different token order and spelling;
- source identifiers are incompatible;
- coordinates differ slightly;
- ratings and amenities can be missing;
- prices and availability change at different times.

Publishing these observations directly would duplicate properties and give downstream consumers conflicting facts.

## The implemented flow

```text
Synthetic source observations
  -> immutable source records and IDs
  -> text/address normalization
  -> geographic candidate filtering
  -> explainable match features
  -> auto-match / review / non-match decision
  -> canonical accommodation facts
  -> required-field and freshness checks
  -> rate, demand, and availability features
  -> evidence-backed commercial actions
```

## Engineering decisions

### Preserve source lineage

Every canonical property retains its source record IDs and provider names. A consumer can trace a recommendation back to the records that produced it.

### Separate matching from survivorship

Entity resolution decides which records describe the same property. Survivorship rules then decide which source supplies the canonical name, address, rating, and other fields. Keeping these steps separate makes the logic easier to test and audit.

### Expose matching evidence

The pipeline stores normalized-name similarity, address similarity, geographic distance, total score, and decision for each candidate pair. Uncertain matches are not silently merged; the architecture reserves a review path.

### Build the facts layer before the AI layer

The commercial actions are deterministic and explainable in this prototype. A learned recommendation model can replace or augment those rules later, but only after property identity, freshness, and source quality are measurable.

## Demonstrated outcomes

- 12 source observations resolved into 5 canonical properties
- 7 duplicate observations merged with lineage retained
- 96 automated quality checks executed
- A deliberately stale observation detected by the freshness control
- Channel-rate spread, demand, and inventory converted into explainable actions
- Five unit tests covering resolution, lineage, quality, and recommendation evidence

## Mapping to a cloud data platform

| Prototype responsibility | Scaled implementation |
|---|---|
| JSON source observations | Cloud Storage plus immutable raw tables |
| Python normalization | Dataflow, Spark, or Python batch workers |
| Candidate scoring | BigQuery SQL/Python, Spark, or a model-serving workflow |
| Canonical facts | Partitioned and clustered BigQuery tables |
| Orchestration | Airflow / Cloud Composer |
| Transformations and tests | dbt contracts, tests, and documentation |
| Event-shaped updates | Pub/Sub or Kafka |
| Quality and ownership | Soda, catalog/lineage tooling, freshness SLOs |
| Decision consumers | APIs, analytics, forecasting, and AI products |

## Five-minute reviewer walkthrough

1. Open **Market pulse** and inspect one rate-parity or demand action.
2. Open **Property resolution** and compare the source names, coordinates, and match scores.
3. Inspect the canonical property IDs and preserved source record IDs.
4. Open **Data quality** and find the stale-source warning.
5. Open **Engineering notes** to see how the demo maps to a larger cloud platform.

## What I would implement next

- Labelled match data and precision/recall evaluation
- Human review workflow for uncertain pairs
- Field-level provenance and confidence
- Slowly changing observation history
- Data contracts and quality/freshness SLOs
- BigQuery partitioning and clustering cost tests
- Model monitoring for learned matching or recommendation components
