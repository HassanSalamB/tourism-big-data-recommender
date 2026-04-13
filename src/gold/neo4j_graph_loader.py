from __future__ import annotations

import os
import sys
import time

from neo4j.exceptions import ServiceUnavailable
from neo4j import GraphDatabase

if __package__ in (None, ""):
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.connections import conn_env, neo4j_env


class Neo4jImporter:
    def __init__(self, uri, auth):
        # The Neo4j driver owns its own connection pool; keep one importer per run.
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def ensure_constraints(self):
        with self.driver.session() as session:
            # Uniqueness makes MERGE predictable and prevents duplicate graph nodes.
            session.run(
                "CREATE CONSTRAINT poi_id IF NOT EXISTS FOR (p:POI) REQUIRE p.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT city_name IF NOT EXISTS FOR (city:City) REQUIRE city.name IS UNIQUE"
            )

    def import_batch(self, batch):
        with self.driver.session() as session:
            # Delete refreshed POIs first so stale relationships disappear.
            session.run(
                """
                UNWIND $batch AS item
                MATCH (existing:POI {id: item.id})
                DETACH DELETE existing
                """,
                batch=batch,
            )
            session.run(
                """
                UNWIND $batch AS item
                MERGE (p:POI {id: item.id})
                SET p.label = item.label,
                    p.latitude = item.latitude,
                    p.longitude = item.longitude,
                    p.country = item.country,
                    p.description = item.description
                MERGE (city:City {name: item.city})
                MERGE (p)-[:LOCATED_IN]->(city)
                FOREACH (category_name IN item.categories |
                    // FOREACH is Cypher's batch-friendly way to create zero or more category links.
                    MERGE (c:Category {name: category_name})
                    MERGE (p)-[:HAS_CATEGORY]->(c)
                )
                """,
                batch=batch,
            )


def _changed_silver_count(conn) -> int:
    with conn.cursor() as cursor:
        # If silver did not change after the last graph sync, Neo4j can be skipped.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM silver_places
            WHERE neo4j_synced_at IS NULL OR updated_at > neo4j_synced_at
            """
        )
        return cursor.fetchone()[0]


def _stream_changed_silver_rows(conn, batch_size: int = 5000):
    # The named cursor streams from Postgres; it avoids loading all silver POIs into RAM.
    query = """
    SELECT
        p.id,
        p.name,
        p.lat,
        p.lon,
        p.city,
        p.country,
        p.description,
        COALESCE(
            ARRAY_AGG(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),
            ARRAY[]::TEXT[]
        ) AS categories
    FROM silver_places p
    LEFT JOIN silver_place_categories pc ON p.id = pc.place_id
    LEFT JOIN silver_categories c ON pc.category_id = c.id
    WHERE p.neo4j_synced_at IS NULL OR p.updated_at > p.neo4j_synced_at
    GROUP BY p.id, p.name, p.lat, p.lon, p.city, p.country, p.description
    """
    with conn.cursor(name="neo4j_silver_stream") as stream:
        stream.itersize = batch_size
        stream.execute(query)
        for row in stream:
            # Neo4j receives one dict per POI; category arrays become HAS_CATEGORY relationships.
            yield {
                "id": row[0],
                "label": row[1] or "Unknown POI",
                "latitude": row[2],
                "longitude": row[3],
                "city": row[4] or "Unknown City",
                "country": row[5],
                "description": row[6],
                "categories": list(row[7] or []),
            }


def _mark_rows_as_synced(conn, ids):
    if not ids:
        return
    with conn.cursor() as cursor:
        # Mark only after a successful Neo4j write so failed batches retry next run.
        cursor.execute(
            "UPDATE silver_places SET neo4j_synced_at = CURRENT_TIMESTAMP WHERE id = ANY(%s)",
            (ids,),
        )
    conn.commit()


def run_neo4j_graph_load(batch_size: int = 500):
    print("[Pipeline] Neo4j graph load: start")
    read_conn = conn_env()
    write_conn = None
    try:
        changed_count = _changed_silver_count(read_conn)
        if changed_count == 0:
            print("[Neo4j] Skip: no silver changes since last graph sync.")
            return

        print(f"[Neo4j] Streaming {changed_count} changed silver rows to Neo4j...")
        uri, auth = neo4j_env()
        print(f"[Neo4j] Connecting to {uri}")
        importer = Neo4jImporter(uri, auth)
        try:
            for attempt in range(1, 13):
                try:
                    importer.ensure_constraints()
                    break
                except ServiceUnavailable as exc:
                    # Compose can mark the Neo4j container "started" before Bolt is ready.
                    if attempt == 12:
                        raise
                    print(
                        f"[Neo4j] Waiting for Neo4j connection "
                        f"(attempt {attempt}/12): {exc}"
                    )
                    time.sleep(5)

            batch = []
            synced_ids = []
            total = 0
            # Use a separate Postgres connection for sync updates so commits do not
            # invalidate the named streaming cursor on `read_conn`.
            write_conn = conn_env()

            for row in _stream_changed_silver_rows(read_conn):
                batch.append(row)
                synced_ids.append(row["id"])

                if len(batch) < batch_size:
                    continue

                importer.import_batch(batch)
                _mark_rows_as_synced(write_conn, synced_ids)
                total += len(batch)
                print(f"[Neo4j] Total processed: {total}/{changed_count}")
                batch.clear()
                synced_ids.clear()

            if batch:
                importer.import_batch(batch)
                _mark_rows_as_synced(write_conn, synced_ids)
                total += len(batch)

            print(f"[Neo4j] Finished. Total {total} POIs stored.")
        finally:
            importer.close()
    finally:
        read_conn.close()
        if write_conn is not None:
            write_conn.close()

    print("[Pipeline] Neo4j graph load: done")


if __name__ == "__main__":
    run_neo4j_graph_load()
