# Holiday Itinerary Planning

This context defines the language used to turn tourism-supply records and traveller preferences into explainable multi-day plans without confusing source coverage, recommendations, and operational evidence.

## Language

**Point of Interest**:
A tourism place supplied by the source feed that may be considered for a plan.
_Avoid_: Attraction, destination

**Destination**:
A city or locality within which a traveller asks the product to construct a plan.
_Avoid_: Place, location

**Interest**:
A traveller-selected category used to restrict or rank candidate Points of Interest.
_Avoid_: Preference filter, tag

**Candidate Place**:
A Point of Interest eligible for the current Destination and selected Interests before daily planning.
_Avoid_: Recommendation, result

**Day Plan**:
An ordered collection of planned stops assigned to one day.
_Avoid_: Cluster, route

**Itinerary**:
One or more Day Plans produced for a traveller’s Destination, duration, pace, and Interests.
_Avoid_: Recommendation, trip

**Related Place**:
A Point of Interest connected to a planned stop through shared tourism categories within the same Destination.
_Avoid_: Similar attraction, recommendation

**Source Snapshot**:
A versioned DATAtourisme archive considered as one ingestion input.
_Avoid_: Dataset, feed run

**Changed Record**:
A source Point of Interest whose canonical content differs from the last ingested version.
_Avoid_: New record, updated row

**Trusted Place**:
A normalized Point of Interest that satisfies the project’s required identity and geographic quality rules.
_Avoid_: Clean record, Silver row

**Planning Signal**:
A measurable input or outcome that can influence or evaluate an Itinerary, such as Interest coverage, travel distance, graph relationships, or weather suitability.
_Avoid_: AI score, recommendation score

**Portfolio Sample**:
A curated set of tourism records used by the public demonstration when the full data platform is not connected.
_Avoid_: Live destination data

**Recorded Evidence**:
A screenshot or artifact captured from a verified full-stack execution and displayed while that environment is offline.
_Avoid_: Live backend

**Live Backend**:
A currently reachable private platform whose public links and health have been deliberately enabled.
_Avoid_: Online demo, recorded system
