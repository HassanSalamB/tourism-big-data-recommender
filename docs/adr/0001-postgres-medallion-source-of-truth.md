---
status: accepted
---

# Keep replayable source and trusted tourism data in PostgreSQL

The platform preserves raw DATAtourisme payloads as Bronze JSONB, normalizes trusted entities into Silver relations, and publishes decision-oriented Gold outputs from the same PostgreSQL source of truth. Separate object and document stores could scale independently, but PostgreSQL keeps the portfolio operable on one machine while content hashes retain incremental replay and audit behavior.

## Consequences

Large-scale deployment should move archives and Parquet snapshots to object storage, but downstream modules must continue to consume trusted records rather than source-specific JSON.
