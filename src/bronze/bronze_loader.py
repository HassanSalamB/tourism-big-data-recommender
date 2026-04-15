"""
Bronze loader: parse ZIP POI objects and upsert them into Postgres bronze tables.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from io import TextIOWrapper

import ijson
from psycopg2.extras import Json, execute_values

if __package__ in (None, ""):
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils.connections import conn_env  # type: ignore
else:
    from utils.connections import conn_env


def _metadata_path(zip_path: str) -> str:
    return f"{zip_path}.metadata.json"


def _load_zip_metadata(zip_path: str) -> dict:
    metadata_file = _metadata_path(zip_path)
    if not os.path.exists(metadata_file):
        return {}
    try:
        with open(metadata_file, encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_zip_metadata_fields(zip_path: str, updates: dict) -> None:
    metadata = _load_zip_metadata(zip_path)
    metadata.update({key: value for key, value in updates.items() if value is not None})
    with open(_metadata_path(zip_path), "w", encoding="utf-8") as file_obj:
        json.dump(metadata, file_obj, indent=2)


def bronze_has_rows(cursor) -> bool:
    cursor.execute("SELECT EXISTS (SELECT 1 FROM bronze_raw_poi LIMIT 1)")
    return cursor.fetchone()[0]


def should_skip_bronze_ingest_from_token_filename(cursor, zip_path: str) -> bool:
    # `token_filename` and `last_ingested_token_filename` both live in the
    # local metadata file (`<zip>.metadata.json`) written by data_api.py.
    metadata = _load_zip_metadata(zip_path)
    current_token_filename = metadata.get("token_filename")
    if not current_token_filename:
        return False
    if not bronze_has_rows(cursor):
        return False
    last_ingested_token_filename = metadata.get("last_ingested_token_filename")
    if not last_ingested_token_filename:
        print("[Bronze API] Bootstrapping ingest marker from existing bronze data.")
        mark_bronze_token_filename_ingested(zip_path)
        return True
    if current_token_filename != last_ingested_token_filename:
        return False
    print("[Bronze API] Token filename already ingested. Skipping bronze ZIP reload.")
    return True


def mark_bronze_token_filename_ingested(zip_path: str) -> None:
    metadata = _load_zip_metadata(zip_path)
    current_token_filename = metadata.get("token_filename")
    if not current_token_filename:
        return
    _save_zip_metadata_fields(
        zip_path,
        {"last_ingested_token_filename": current_token_filename},
    )


def ensure_bronze_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze_raw_poi (
            id TEXT PRIMARY KEY,
            source_identifier TEXT,
            raw_payload JSONB NOT NULL,
            source_file TEXT,
            content_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bronze_raw_poi_source_identifier "
        "ON bronze_raw_poi(source_identifier)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bronze_raw_poi_content_hash "
        "ON bronze_raw_poi(content_hash)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bronze_raw_poi_updated_at "
        "ON bronze_raw_poi(updated_at)"
    )


def _iter_json_items_from_zip(zipped, file_name: str):
    try:
        with zipped.open(file_name) as raw_file:
            parser = ijson.parse(TextIOWrapper(raw_file, encoding="utf-8"))
            top_level_event = None
            for prefix, event, _ in parser:
                if prefix == "" and event in {"start_array", "start_map"}:
                    top_level_event = event
                    break
    except Exception as exc:
        print(f"[Bronze API] Skipping unreadable file {file_name}: {exc}")
        return

    item_prefix = "item" if top_level_event == "start_array" else ""
    if top_level_event not in {"start_array", "start_map"}:
        print(f"[Bronze API] Skipping unsupported JSON structure in {file_name}")
        return

    try:
        with zipped.open(file_name) as raw_file:
            stream = TextIOWrapper(raw_file, encoding="utf-8")
            for item in ijson.items(stream, item_prefix):
                if isinstance(item, dict):
                    yield item
    except Exception as exc:
        print(f"[Bronze API] Skipping unreadable file {file_name}: {exc}")


def _iter_zip_objects(zip_path: str):
    with zipfile.ZipFile(zip_path) as zipped:
        for file_name in zipped.namelist():
            if not file_name.startswith("objects/") or not file_name.endswith(".json"):
                continue
            for item in _iter_json_items_from_zip(zipped, file_name):
                poi_id = item.get("@id")
                if not poi_id:
                    continue
                content_hash = hashlib.sha256(
                    json.dumps(item, sort_keys=True, ensure_ascii=True).encode("utf-8")
                ).hexdigest()
                yield poi_id, item.get("dc:identifier"), item, file_name, content_hash


def _existing_hashes_for_ids(cursor, ids):
    if not ids:
        return {}
    cursor.execute(
        "SELECT id, content_hash FROM bronze_raw_poi WHERE id = ANY(%s)",
        (ids,),
    )
    return dict(cursor.fetchall())


def _flush_bronze_batch(cursor, pending_items, counts):
    if not pending_items:
        return

    # Fetch current hashes once for the whole batch to avoid per-row queries.
    existing_hashes = _existing_hashes_for_ids(cursor, [item["poi_id"] for item in pending_items])
    rows_to_upsert = []

    for current in pending_items:
        existing_hash = existing_hashes.get(current["poi_id"])
        if existing_hash == current["content_hash"]:
            counts["unchanged"] += 1
            counts["total"] += 1
            continue

        rows_to_upsert.append(
            (
                current["poi_id"],
                current["source_identifier"],
                Json(current["raw_payload"]),
                current["source_file"],
                current["content_hash"],
            )
        )
        counts["total"] += 1
        if existing_hash is None:
            counts["inserted"] += 1
        else:
            counts["updated"] += 1

    if rows_to_upsert:
        execute_values(
            cursor,
            """
            INSERT INTO bronze_raw_poi(
                id,
                source_identifier,
                raw_payload,
                source_file,
                content_hash
            )
            VALUES %s
            ON CONFLICT (id) DO UPDATE
            SET
                source_identifier = EXCLUDED.source_identifier,
                raw_payload = EXCLUDED.raw_payload,
                source_file = EXCLUDED.source_file,
                content_hash = EXCLUDED.content_hash,
                updated_at = CURRENT_TIMESTAMP,
                ingested_at = CURRENT_TIMESTAMP
            """,
            rows_to_upsert,
        )


def ingest_zip_to_postgres(conn, cursor, zip_path: str, batch_size: int = 1000):
    counts = {"total": 0, "inserted": 0, "updated": 0, "unchanged": 0}
    pending_items = []
    print("[Bronze API] Loading ZIP contents into Postgres bronze_raw_poi...")

    for poi_id, source_identifier, raw_payload, source_file, content_hash in _iter_zip_objects(zip_path):
        pending_items.append(
            {
                "poi_id": poi_id,
                "source_identifier": source_identifier,
                "raw_payload": raw_payload,
                "source_file": source_file,
                "content_hash": content_hash,
            }
        )

        if len(pending_items) < batch_size:
            continue

        _flush_bronze_batch(cursor, pending_items, counts)
        conn.commit()
        print(
            f"[Bronze API] Processed {counts['total']} raw objects "
            f"(new: {counts['inserted']}, changed: {counts['updated']}, "
            f"unchanged: {counts['unchanged']})..."
        )
        pending_items.clear()

    _flush_bronze_batch(cursor, pending_items, counts)
    conn.commit()
    print(
        f"[Bronze API] Bronze load complete. Total raw objects: {counts['total']} "
        f"(new: {counts['inserted']}, changed: {counts['updated']}, "
        f"unchanged: {counts['unchanged']})"
    )
    return counts


def run_bronze_loader(zip_path: str, batch_size: int = 1000) -> dict:
    """Load local ZIP into bronze tables (new/changed rows only)."""
    print("[Pipeline] Bronze load: start")
    try:
        with conn_env() as conn:
            with conn.cursor() as cursor:
                print("[Bronze API] Connected to Postgres")
                ensure_bronze_table(cursor)
                conn.commit()
                if should_skip_bronze_ingest_from_token_filename(cursor, zip_path):
                    print("[Bronze API] Bronze ingest skipped: unchanged token filename already loaded.")
                    print("[Pipeline] Bronze load: done")
                    # Contract for pipeline:
                    # {"ok": bool, "skipped_ingest": bool, "counts": dict|None}
                    return {
                        "ok": True,
                        "skipped_ingest": True,
                        "counts": {"total": 0, "inserted": 0, "updated": 0, "unchanged": 0},
                    }
                counts = ingest_zip_to_postgres(conn, cursor, zip_path, batch_size=batch_size)
                mark_bronze_token_filename_ingested(zip_path)
                print("[Pipeline] Bronze load: done")
                return {
                    "ok": True,
                    "skipped_ingest": False,
                    "counts": counts,
                }
    except Exception as exc:
        print(f"[Bronze API] Error during bronze load: {exc}")
        return {
            "ok": False,
            "skipped_ingest": False,
            "counts": None,
            "error": str(exc),
        }
