---
status: accepted
---

# Plan from trusted places and enrich through the graph

Itineraries select actual trusted Points of Interest for one Destination, use geographic grouping to form Day Plans, and then enrich selected stops with Neo4j Related Places. Gold spatial clusters are analytical summaries rather than itinerary candidates, which keeps the user response explainable at place level.

## Consequences

Neo4j enrichment may fail without blocking plan generation, while any future ranking model must return identifiable Points of Interest rather than opaque cluster summaries.
