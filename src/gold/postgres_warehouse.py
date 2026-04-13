"""Gold layer: build business-ready cluster tables from cleaned silver data."""

import os
import sys

import h3
import pandas as pd
from psycopg2.extras import execute_values

if __package__ in (None, ""):
    # Allow running the file directly with `python src/gold/postgres_warehouse.py`.
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.connections import conn_env


def _score_categories(category_text: pd.Series) -> pd.Series:
    # Gold scoring is business logic, not cleaning: silver already prepared usable rows.
    category_text = category_text.astype("string").str.lower().fillna("")
    score = pd.Series(1, index=category_text.index, dtype="int64")
    score = score.mask(category_text.str.contains("museum", regex=False), score + 3)
    score = score.mask(category_text.str.contains("park", regex=False), score + 2)
    score = score.mask(category_text.str.contains("restaurant", regex=False), score + 1)
    score = score.mask(category_text.str.contains("heritage", regex=False), score + 2)
    score = score.mask(category_text.str.contains("cultural", regex=False), score + 2)
    return score


def generate_itinerary(clusters, sample_city, days=3, max_places_per_day=5):
    # The itinerary is just a readable sample built from the top-ranked clusters.
    if sample_city is None:
        print("No city provided for itinerary generation.")
        return []
    city_clusters = [cluster for cluster in clusters if cluster["city"] == sample_city]
    if not city_clusters:
        print(f"No data for city: {sample_city}")
        return []
    top_clusters = city_clusters[:days]
    itinerary = []
    for i, row in enumerate(top_clusters, start=1):
        itinerary.append(
            {
                "day": i,
                "area": row["h3_index"],
                "poi_count": row["poi_count"],
                "places": row["name"][:max_places_per_day],
            }
        )
    return itinerary


def _rows_to_dataframe(rows, columns) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)


def _stream_silver_chunks(conn, batch_size: int):
    # Aggregate categories in SQL so each pandas row represents one POI.
    query = """
SELECT
    p.id,
    p.name,
    p.lat,
    p.lon,
    p.city,
    COALESCE(
        ARRAY_AGG(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),
        ARRAY[]::TEXT[]
    ) AS categories
FROM silver_places p
LEFT JOIN silver_place_categories pc ON p.id = pc.place_id
LEFT JOIN silver_categories c ON pc.category_id = c.id
GROUP BY
    p.id,
    p.name,
    p.lat,
    p.lon,
    p.city
ORDER BY p.id
"""
    with conn.cursor(name="gold_silver_stream") as stream:
        stream.itersize = batch_size
        stream.execute(query)
        columns = [desc[0] for desc in stream.description]
        while True:
            # Keep gold memory bounded even if silver contains hundreds of thousands of POIs.
            rows = stream.fetchmany(batch_size)
            if not rows:
                break
            yield _rows_to_dataframe(rows, columns)


def _prepare_gold_chunk(chunk: pd.DataFrame, h3_resolution: int) -> pd.DataFrame:
    chunk = chunk.copy()
    if chunk.empty:
        return chunk

    chunk["category_text"] = chunk["categories"].map(
        lambda categories: " ".join(categories) if isinstance(categories, list) else ""
    )
    chunk["score"] = _score_categories(chunk["category_text"])
    # H3 turns lat/lon points into grid cells so nearby POIs can be clustered.
    chunk["h3_index"] = chunk.apply(
        lambda row: h3.latlng_to_cell(row["lat"], row["lon"], h3_resolution),
        axis=1,
    )
    return chunk.loc[:, ["id", "name", "city", "score", "h3_index"]]


def _merge_cluster_frame(clusters: dict, cluster_frame: pd.DataFrame):
    if cluster_frame.empty:
        return
    for row in cluster_frame.itertuples(index=False):
        # The dict keeps accumulated state across chunks without holding every raw row.
        cluster = clusters.setdefault(
            row.h3_index,
            {
                "h3_index": row.h3_index,
                "city": row.city,
                "score": 0,
                "place_ids": set(),
                "places": [],
                "place_names": set(),
            },
        )
        if not cluster["city"] and row.city:
            cluster["city"] = row.city
        cluster["score"] += row.score
        cluster["place_ids"].add(row.id)
        if row.name not in cluster["place_names"]:
            cluster["place_names"].add(row.name)
            if len(cluster["places"]) < 5:
                # Keep only a few sample names per cluster for readable itinerary output.
                cluster["places"].append(row.name)


def _load_clusters_streaming(conn, h3_resolution: int, batch_size: int = 5000):
    clusters = {}
    city_counts = pd.Series(dtype="int64")
    rows_loaded = 0

    for chunk in _stream_silver_chunks(conn, batch_size):
        rows_loaded += len(chunk)
        prepared = _prepare_gold_chunk(chunk, h3_resolution)
        _merge_cluster_frame(clusters, prepared)
        # `value_counts` is chunk-local, then `.add(..., fill_value=0)` merges totals.
        city_counts = city_counts.add(prepared["city"].value_counts(), fill_value=0)

        if rows_loaded % 50000 == 0:
            print(f"[Gold] Streamed {rows_loaded} silver rows...")

    usable_clusters = []
    for cluster in clusters.values():
        poi_count = len(cluster["place_ids"])
        if poi_count < 2:
            # Single-POI cells are less useful for itinerary area suggestions.
            continue
        usable_clusters.append(
            {
                "h3_index": cluster["h3_index"],
                "city": cluster["city"],
                "score": cluster["score"],
                "poi_count": poi_count,
                "name": cluster["places"],
            }
        )

    usable_clusters.sort(
        key=lambda item: (item["score"], item["poi_count"]),
        reverse=True,
    )
    return rows_loaded, usable_clusters, city_counts.astype("int64")


def _ensure_gold_clusters(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS gold_clusters (
            h3_index TEXT PRIMARY KEY,
            city TEXT,
            total_score FLOAT,
            poi_count INTEGER
        )
        """
    )


def _write_gold_clusters(cursor, clusters):
    _ensure_gold_clusters(cursor)
    cursor.execute("TRUNCATE TABLE gold_clusters")
    execute_values(
        cursor,
        """
        INSERT INTO gold_clusters (h3_index, city, total_score, poi_count)
        VALUES %s
        """,
        [
            (
                cluster["h3_index"],
                cluster["city"],
                cluster["score"],
                cluster["poi_count"],
            )
            for cluster in clusters
        ],
    )


def run_gold_postgres_dw(h3_resolution: int = 8):
    print("[Pipeline] Gold Postgres DW: start")
    conn = conn_env()
    cursor = conn.cursor()
    cursor.execute("SELECT current_database();")
    print("[Gold] Connected to DB:", cursor.fetchone()[0])
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM silver_places
        WHERE gold_pg_synced_at IS NULL OR updated_at > gold_pg_synced_at
        """
    )
    changed_count = cursor.fetchone()[0]
    # Gold Postgres is derived from silver, so we can skip the expensive rebuild if nothing changed.
    if changed_count == 0:
        conn.close()
        print("[Gold] Skip: no silver changes since last warehouse sync.")
        print("[Pipeline] Gold Postgres DW: done")
        return

    print("[Gold] Streaming silver rows from Postgres...")
    rows_loaded, clusters, city_counts = _load_clusters_streaming(conn, h3_resolution)
    print(f"[Gold] Loaded {rows_loaded} silver rows")

    if not clusters:
        print("[Gold] No usable rows found. Exiting gold stage.")
        conn.close()
        print("[Pipeline] Gold Postgres DW: done (empty)")
        return

    print(f"[Gold] Created {len(clusters)} clusters")
    _write_gold_clusters(cursor, clusters)
    conn.commit()

    top_cities = city_counts.sort_values(ascending=False)
    # Pick the densest city as a deterministic sample for console output.
    sample_city = top_cities.index[0] if not top_cities.empty else None
    print(f"\n[Gold] Sample itinerary - city: {sample_city}\n")
    itinerary = generate_itinerary(clusters, sample_city, days=3, max_places_per_day=5)
    if not itinerary:
        print("No itinerary could be generated.")
    else:
        for day in itinerary:
            print(f"Day {day['day']}:")
            print(f"Area: {day['area']} | POIs in cluster: {day['poi_count']}")
            for place in day["places"]:
                print(" -", place)
            print()

    print("[Gold] Top cities by POI count:")
    for city, count in top_cities.head(10).items():
        print(f"{city}: {count}")
    cursor.execute(
        """
        UPDATE silver_places
        SET gold_pg_synced_at = CURRENT_TIMESTAMP
        WHERE gold_pg_synced_at IS NULL OR updated_at > gold_pg_synced_at
        """
    )
    conn.commit()

    conn.close()
    print("[Gold] Gold layer completed successfully")
    print("[Pipeline] Gold Postgres DW: done")


if __name__ == "__main__":
    run_gold_postgres_dw()
