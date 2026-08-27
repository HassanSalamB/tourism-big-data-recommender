"""Transparent accommodation matching, quality, and decision-support pipeline.

The demo intentionally uses deterministic, explainable logic. In a production
system the same feature set can feed a learned entity-resolution model, while
human review remains available for uncertain matches.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


DATA_PATH = Path(__file__).parent / "data" / "accommodation_sources.json"
SOURCE_PRIORITY = {"HotelDirect": 0, "StayFinder": 1, "TravelHub": 2}
AUTO_MATCH_THRESHOLD = 0.78
REVIEW_THRESHOLD = 0.64


def load_source_records(path: Path = DATA_PATH) -> list[dict[str, Any]]:
    """Load the synthetic, public-safe accommodation observations."""

    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    """Normalize spelling and punctuation without hiding the original value."""

    if value is None:
        return ""
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore")
    normalized = re.sub(r"[^a-z0-9]+", " ", ascii_value.decode().lower())
    aliases = {"gent": "ghent", "wi fi": "wifi", "internet": "wifi"}
    tokens = [aliases.get(token, token) for token in normalized.split()]
    return " ".join(tokens)


def _token_signature(value: Any) -> str:
    ignored = {"hotel", "the", "ghent", "gent", "belgium", "be"}
    tokens = [token for token in normalize_text(value).split() if token not in ignored]
    return " ".join(sorted(tokens))


def _similarity(left: Any, right: Any, *, tokenized: bool = False) -> float:
    normalizer = _token_signature if tokenized else normalize_text
    left_normalized = normalizer(left)
    right_normalized = normalizer(right)
    if not left_normalized or not right_normalized:
        return 0.0
    return SequenceMatcher(None, left_normalized, right_normalized).ratio()


def haversine_km(left: dict[str, Any], right: dict[str, Any]) -> float:
    """Return distance between two observations in kilometres."""

    lat1, lon1 = math.radians(left["latitude"]), math.radians(left["longitude"])
    lat2, lon2 = math.radians(right["latitude"]), math.radians(right["longitude"])
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def score_candidate(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Score a possible cross-source duplicate and preserve feature evidence."""

    same_source = left["source"] == right["source"]
    same_city = normalize_text(left["city"]) == normalize_text(right["city"])
    distance_km = haversine_km(left, right)
    name_similarity = _similarity(left["name"], right["name"], tokenized=True)
    address_similarity = _similarity(left["address"], right["address"], tokenized=True)
    geo_similarity = max(0.0, 1.0 - distance_km / 0.75)
    score = 0.52 * name_similarity + 0.28 * address_similarity + 0.20 * geo_similarity

    if same_source or not same_city or distance_km > 1.5:
        decision = "not_match"
    elif score >= AUTO_MATCH_THRESHOLD:
        decision = "auto_match"
    elif score >= REVIEW_THRESHOLD:
        decision = "review"
    else:
        decision = "not_match"

    return {
        "left_id": left["source_property_id"],
        "right_id": right["source_property_id"],
        "left_name": left["name"],
        "right_name": right["name"],
        "name_similarity": round(name_similarity, 3),
        "address_similarity": round(address_similarity, 3),
        "distance_km": round(distance_km, 3),
        "match_score": round(score, 3),
        "decision": decision,
    }


def candidate_pairs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate scored cross-source candidate pairs."""

    pairs = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            score = score_candidate(left, right)
            if score["decision"] != "not_match":
                pairs.append(score)
    return sorted(pairs, key=lambda item: item["match_score"], reverse=True)


class _UnionFind:
    def __init__(self, ids: Iterable[str]):
        self.parent = {record_id: record_id for record_id in ids}

    def find(self, record_id: str) -> str:
        root = record_id
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[record_id] != record_id:
            parent = self.parent[record_id]
            self.parent[record_id] = root
            record_id = parent
        return root

    def union(self, left_id: str, right_id: str) -> None:
        left_root, right_root = self.find(left_id), self.find(right_id)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _preferred(records: list[dict[str, Any]], field: str) -> Any:
    candidates = [record for record in records if record.get(field) not in (None, "", [])]
    if not candidates:
        return None
    candidates.sort(
        key=lambda record: (
            SOURCE_PRIORITY.get(record["source"], 99),
            -len(str(record.get(field, ""))),
        )
    )
    return candidates[0][field]


def _canonical_id(records: list[dict[str, Any]]) -> str:
    identity = "|".join(sorted(record["source_property_id"] for record in records))
    return "acc_" + hashlib.sha1(identity.encode("utf-8")).hexdigest()[:10]


def _canonicalize(records: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [float(record["room_rate"]) for record in records if record.get("room_rate") is not None]
    demand = [float(record["demand_index"]) for record in records if record.get("demand_index") is not None]
    rooms = [int(record["available_rooms"]) for record in records if record.get("available_rooms") is not None]
    reviews = [float(record["review_score"]) for record in records if record.get("review_score") is not None]
    amenities = sorted(
        {
            normalize_text(amenity)
            for record in records
            for amenity in record.get("amenities", [])
            if normalize_text(amenity)
        }
    )
    minimum_rate = min(rates) if rates else None
    maximum_rate = max(rates) if rates else None
    spread_pct = (
        ((maximum_rate - minimum_rate) / minimum_rate * 100)
        if minimum_rate and maximum_rate is not None
        else 0.0
    )
    timestamps = [datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00")) for record in records]

    return {
        "canonical_id": _canonical_id(records),
        "name": _preferred(records, "name"),
        "address": _preferred(records, "address"),
        "city": "Ghent" if normalize_text(_preferred(records, "city")) == "ghent" else _preferred(records, "city"),
        "country": "Belgium",
        "latitude": round(mean(record["latitude"] for record in records), 6),
        "longitude": round(mean(record["longitude"] for record in records), 6),
        "star_rating": _preferred(records, "star_rating"),
        "review_score": round(mean(reviews), 2) if reviews else None,
        "amenities": amenities,
        "source_count": len({record["source"] for record in records}),
        "source_records": [record["source_property_id"] for record in records],
        "sources": sorted({record["source"] for record in records}),
        "minimum_rate": minimum_rate,
        "maximum_rate": maximum_rate,
        "rate_spread_pct": round(spread_pct, 1),
        "available_rooms": min(rooms) if rooms else None,
        "demand_index": round(mean(demand), 2) if demand else None,
        "latest_observation": max(timestamps).isoformat().replace("+00:00", "Z"),
        "records": sorted(records, key=lambda record: SOURCE_PRIORITY.get(record["source"], 99)),
    }


def resolve_entities(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve accepted pairs into canonical accommodation records."""

    pairs = candidate_pairs(records)
    union_find = _UnionFind(record["source_property_id"] for record in records)
    for pair in pairs:
        if pair["decision"] == "auto_match":
            union_find.union(pair["left_id"], pair["right_id"])

    clusters: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        root = union_find.find(record["source_property_id"])
        clusters.setdefault(root, []).append(record)

    canonical = [_canonicalize(cluster) for cluster in clusters.values()]
    canonical.sort(key=lambda record: record["name"])
    return canonical, pairs


def quality_report(
    records: list[dict[str, Any]], canonical: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create row-level quality issues and aggregate quality KPIs."""

    required_fields = ("name", "address", "city", "latitude", "longitude", "room_rate", "observed_at")
    reference_time = max(
        datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00")) for record in records
    )
    issues: list[dict[str, Any]] = []
    checks = 0
    failures = 0

    for record in records:
        for field in required_fields:
            checks += 1
            if record.get(field) in (None, "", []):
                failures += 1
                issues.append(
                    {
                        "severity": "error",
                        "record_id": record["source_property_id"],
                        "check": f"required_{field}",
                        "detail": f"{field} is missing",
                    }
                )

        checks += 1
        observed = datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))
        age_hours = (reference_time - observed).total_seconds() / 3600
        if age_hours > 72:
            failures += 1
            issues.append(
                {
                    "severity": "warning",
                    "record_id": record["source_property_id"],
                    "check": "freshness_72h",
                    "detail": f"Observation is {age_hours:.0f} hours older than the latest source record",
                }
            )

    merged_rows = sum(max(0, item["source_count"] - 1) for item in canonical)
    return issues, {
        "checks_run": checks,
        "checks_passed": checks - failures,
        "quality_pass_rate": round((checks - failures) / checks * 100, 1) if checks else 100.0,
        "duplicate_rows_merged": merged_rows,
        "canonical_properties": len(canonical),
        "source_rows": len(records),
    }


def recommendations(canonical: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate explainable commercial actions from trusted canonical records."""

    actions = []
    for property_record in canonical:
        if property_record["rate_spread_pct"] >= 10:
            action = "Review channel rate parity"
            reason = (
                f"Observed rates range from EUR {property_record['minimum_rate']:.0f} to "
                f"EUR {property_record['maximum_rate']:.0f} ({property_record['rate_spread_pct']:.1f}% spread)."
            )
            priority = "high"
        elif property_record["demand_index"] >= 0.8 and property_record["available_rooms"] <= 8:
            action = "Evaluate a controlled rate increase"
            reason = (
                f"Demand index is {property_record['demand_index']:.2f} with only "
                f"{property_record['available_rooms']} rooms visible."
            )
            priority = "high"
        elif property_record["demand_index"] <= 0.45 and property_record["available_rooms"] >= 15:
            action = "Consider a targeted demand campaign"
            reason = (
                f"Demand index is {property_record['demand_index']:.2f} while "
                f"{property_record['available_rooms']} rooms remain visible."
            )
            priority = "medium"
        else:
            action = "Maintain and monitor"
            reason = "Rate consistency, demand, and visible inventory do not cross an action threshold."
            priority = "low"

        actions.append(
            {
                "canonical_id": property_record["canonical_id"],
                "property": property_record["name"],
                "priority": priority,
                "action": action,
                "reason": reason,
                "evidence_sources": property_record["source_count"],
            }
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(actions, key=lambda item: (priority_order[item["priority"]], item["property"]))


def run_demo_pipeline(path: Path = DATA_PATH) -> dict[str, Any]:
    """Run the complete lightweight demo and return review-ready artifacts."""

    records = load_source_records(path)
    canonical, pairs = resolve_entities(records)
    issues, quality = quality_report(records, canonical)
    actions = recommendations(canonical)
    return {
        "source_records": records,
        "canonical_properties": canonical,
        "candidate_pairs": pairs,
        "quality_issues": issues,
        "quality_summary": quality,
        "recommendations": actions,
        "source_distribution": dict(Counter(record["source"] for record in records)),
    }


if __name__ == "__main__":
    output = run_demo_pipeline()
    print(json.dumps(output["quality_summary"], indent=2))
