"""
Bronze layer: request the DATAtourisme feed as a ZIP archive, stream raw POI
documents into Postgres JSONB, and track changes with content hashes.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from io import TextIOWrapper

import ijson
import requests
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

if __package__ in (None, ""):
    # Allow running the file directly with `python src/bronze/api_ingest.py`.
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.config import load_config
from utils.connections import conn_env

load_dotenv()

API_TOKEN = os.getenv("DATATOURISME_TOKEN")
BRONZE_FEED_STATE_NAME = "datatourisme_catalog"


def _metadata_path(zip_path: str) -> str:
    return f"{zip_path}.metadata.json"


def _load_zip_metadata(zip_path: str) -> dict:
    metadata_file = _metadata_path(zip_path)
    if not os.path.exists(metadata_file):
        return {}
    try:
        # Metadata is only a cache hint; corrupt/missing metadata should not stop ingestion.
        with open(metadata_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_zip_metadata(zip_path: str, response) -> None:
    # Store HTTP validators beside the ZIP so the next run can ask the server
    # whether the existing file is still valid before downloading again.
    metadata = {
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
        "content_length": response.headers.get("Content-Length"),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata = {key: value for key, value in metadata.items() if value}
    with open(_metadata_path(zip_path), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def _download_headers(metadata: dict) -> dict:
    headers = {"Accept": "application/zip, application/octet-stream"}
    # Conditional headers let the server return 304 Not Modified when supported.
    if metadata.get("etag"):
        headers["If-None-Match"] = metadata["etag"]
    if metadata.get("last_modified"):
        headers["If-Modified-Since"] = metadata["last_modified"]
    return headers


def _api_key() -> str | None:
    explicit_key = os.getenv("DATATOURISME_API_KEY")
    if explicit_key:
        return explicit_key
    if not API_TOKEN:
        return None
    # The ZIP feed token is stored as `api_key/feed_id`; the catalog API uses only the API key.
    return API_TOKEN.split("/", 1)[0]


def _catalog_api_url(config: dict) -> str:
    return config.get("api", {}).get("catalog_url", "https://api.datatourisme.fr/v1/catalog")


def _fetch_catalog_freshness(config: dict) -> dict | None:
    api_key = _api_key()
    if not api_key:
        print(
            "[Bronze API] Catalog freshness probe skipped: "
            "DATATOURISME_API_KEY/DATATOURISME_TOKEN missing."
        )
        return None

    try:
        # This probe is the best no-download check, but it depends on the API key
        # being authorized for the DATAtourisme catalog endpoint.
        response = requests.get(
            _catalog_api_url(config),
            headers={"X-API-Key": api_key},
            params={
                "fields": config.get("api", {}).get(
                    "catalog_fields",
                    "uuid,lastUpdateDatatourisme",
                ),
                "sort": config.get("api", {}).get(
                    "catalog_sort",
                    "lastUpdateDatatourisme[desc]",
                ),
                "page_size": int(config.get("api", {}).get("catalog_page_size", 1)),
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[Bronze API] Catalog freshness probe failed: {exc}")
        return None

    objects = payload.get("objects") or []
    # We keep a tiny signature instead of storing the whole catalog response.
    latest = objects[0] if objects else {}
    return {
        "total": payload.get("meta", {}).get("total"),
        "latest_uuid": latest.get("uuid"),
        "latest_last_update_datatourisme": latest.get("lastUpdateDatatourisme"),
    }


def _content_length(response) -> int | None:
    try:
        return int(response.headers.get("Content-Length", ""))
    except ValueError:
        return None


def _has_matching_validator(response, metadata: dict) -> bool:
    # ETag is strongest. Last-Modified is weaker, but still useful if the server
    # does not publish Content-Length.
    remote_etag = response.headers.get("ETag")
    if remote_etag and remote_etag == metadata.get("etag"):
        print("[Bronze API] Remote ETag unchanged. Reusing existing ZIP.")
        return True

    remote_last_modified = response.headers.get("Last-Modified")
    if remote_last_modified and remote_last_modified == metadata.get("last_modified"):
        print("[Bronze API] Remote Last-Modified unchanged. Reusing existing ZIP.")
        return True

    return False


def _should_reuse_existing_zip(zip_path: str, remote_size: int | None) -> bool:
    if not os.path.exists(zip_path):
        return False
    if remote_size is None:
        # Without Content-Length or validators, same/different cannot be proven
        # without reading the body, so we fall back to a real download.
        print(
            "[Bronze API] Remote ZIP size is not available; downloading to verify changes."
        )
        return False

    local_size = os.path.getsize(zip_path)
    print(f"[Bronze API] Local ZIP size: {local_size} bytes")
    print(f"[Bronze API] Remote ZIP size: {remote_size} bytes")
    if remote_size == local_size:
        print("[Bronze API] ZIP size unchanged. Reusing existing download.")
        return True

    print("[Bronze API] ZIP size changed. Downloading fresh data.")
    return False


def ensure_bronze_table(cursor):
    # `id` is the raw Datatourisme `@id`; raw_payload keeps the original JSON in Postgres.
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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze_feed_state (
            source_name TEXT PRIMARY KEY,
            total_count INTEGER,
            latest_uuid TEXT,
            latest_last_update_datatourisme TEXT,
            checked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            downloaded_at TIMESTAMPTZ
        )
        """
    )


def _bronze_has_rows(cursor) -> bool:
    cursor.execute("SELECT EXISTS (SELECT 1 FROM bronze_raw_poi LIMIT 1)")
    return cursor.fetchone()[0]


def _load_feed_state(cursor, source_name: str = BRONZE_FEED_STATE_NAME) -> dict | None:
    cursor.execute(
        """
        SELECT total_count, latest_uuid, latest_last_update_datatourisme
        FROM bronze_feed_state
        WHERE source_name = %s
        """,
        (source_name,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "total": row[0],
        "latest_uuid": row[1],
        "latest_last_update_datatourisme": row[2],
    }


def _save_feed_state(
    cursor,
    freshness: dict,
    downloaded: bool,
    source_name: str = BRONZE_FEED_STATE_NAME,
) -> None:
    if not freshness:
        return
    # `downloaded_at` only moves when we actually downloaded the ZIP; `checked_at`
    # moves on every successful catalog probe.
    cursor.execute(
        """
        INSERT INTO bronze_feed_state(
            source_name,
            total_count,
            latest_uuid,
            latest_last_update_datatourisme,
            checked_at,
            downloaded_at
        )
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END)
        ON CONFLICT (source_name) DO UPDATE
        SET total_count = EXCLUDED.total_count,
            latest_uuid = EXCLUDED.latest_uuid,
            latest_last_update_datatourisme = EXCLUDED.latest_last_update_datatourisme,
            checked_at = CURRENT_TIMESTAMP,
            downloaded_at = CASE
                WHEN %s THEN CURRENT_TIMESTAMP
                ELSE bronze_feed_state.downloaded_at
            END
        """,
        (
            source_name,
            freshness.get("total"),
            freshness.get("latest_uuid"),
            freshness.get("latest_last_update_datatourisme"),
            downloaded,
            downloaded,
        ),
    )


def _should_skip_download_from_catalog(cursor, config: dict) -> tuple[bool, dict | None]:
    freshness = _fetch_catalog_freshness(config)
    if not freshness:
        return False, None

    previous = _load_feed_state(cursor)
    # The skip is safe only when both the catalog signature matches and bronze
    # already has rows; an empty bronze table must still be populated.
    if previous == freshness and _bronze_has_rows(cursor):
        print("[Bronze API] Catalog freshness signature unchanged. Skipping ZIP download.")
        _save_feed_state(cursor, freshness, downloaded=False)
        return True, freshness

    print("[Bronze API] Catalog freshness changed or not recorded. ZIP download required.")
    return False, freshness


def _download_zip(url: str, zip_path: str):
    config = load_config()
    api_config = config.get("api", {})
    download_retries = int(api_config.get("download_retries", 3))
    wait_seconds = int(api_config.get("download_wait_seconds", 10))
    chunk_size = int(api_config.get("download_chunk_mb", 1)) * 1024 * 1024
    progress_log_seconds = int(api_config.get("progress_log_seconds", 5))
    full_url = f"{url}{API_TOKEN}" if API_TOKEN else url
    print(f"[Bronze API] Requesting ZIP from {full_url}...")
    metadata = _load_zip_metadata(zip_path)
    headers = _download_headers(metadata)

    for attempt in range(download_retries):
        # `stream=True` avoids loading the whole ZIP response into memory at once.
        with requests.get(full_url, headers=headers, stream=True) as response:
            if response.status_code == 304:
                # 304 is only useful if we still have the local ZIP file from a previous run.
                if os.path.exists(zip_path):
                    print("[Bronze API] Remote ZIP not modified. Reusing existing ZIP.")
                    return zip_path
                raise ValueError("Remote ZIP was not modified, but no local ZIP exists")

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()
                disposition = response.headers.get("Content-Disposition", "").lower()
                # DATAtourisme should return a ZIP; this catches auth/error HTML pages early.
                if (
                    "zip" not in content_type
                    and "octet-stream" not in content_type
                    and ".zip" not in disposition
                ):
                    raise ValueError(
                        f"Expected ZIP payload but received Content-Type={content_type!r}"
                    )
                remote_size = _content_length(response)
                if (
                    os.path.exists(zip_path)
                    and remote_size is None
                    and _has_matching_validator(response, metadata)
                ):
                    return zip_path
                # Size comparison is a cheap fallback when validators are missing.
                if _should_reuse_existing_zip(zip_path, remote_size):
                    _save_zip_metadata(zip_path, response)
                    return zip_path

                os.makedirs(os.path.dirname(zip_path) or ".", exist_ok=True)
                downloaded_bytes = 0
                last_progress_log = time.monotonic()
                with open(zip_path, "wb") as zip_file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            zip_file.write(chunk)
                            downloaded_bytes += len(chunk)
                            now = time.monotonic()
                            # Large feeds can look "stuck"; log progress on a timer, not per chunk.
                            if now - last_progress_log >= progress_log_seconds:
                                downloaded_mb = downloaded_bytes / (1024 * 1024)
                                print(f"[Bronze API] Downloaded {downloaded_mb:.1f} MB...")
                                last_progress_log = now
                _save_zip_metadata(zip_path, response)
                downloaded_mb = downloaded_bytes / (1024 * 1024)
                print(f"[Bronze API] ZIP download complete: {zip_path} ({downloaded_mb:.1f} MB)")
                return zip_path

            if response.status_code == 202:
                print(
                    f"[Bronze API] Waiting for file "
                    f"(attempt {attempt + 1}/{download_retries})..."
                )
                time.sleep(wait_seconds)
                continue

            raise ValueError(f"Download failed with status code {response.status_code}")

    raise ValueError(f"ZIP was not ready after {download_retries} attempts")


def _iter_json_items_from_zip(zf, file_name: str):
    # Detect whether each ZIP entry is a single JSON object or an array of objects,
    # then stream items one-by-one with ijson.
    try:
        with zf.open(file_name) as raw_file:
            parser = ijson.parse(TextIOWrapper(raw_file, encoding="utf-8"))
            top_level_event = None
            for prefix, event, _ in parser:
                # We only need the first structural token to choose the ijson prefix.
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
        with zf.open(file_name) as raw_file:
            stream = TextIOWrapper(raw_file, encoding="utf-8")
            for item in ijson.items(stream, item_prefix):
                # Bronze only stores POI-like objects; malformed values are skipped quietly.
                if isinstance(item, dict):
                    yield item
    except Exception as exc:
        print(f"[Bronze API] Skipping unreadable file {file_name}: {exc}")


def _iter_zip_objects(zip_path: str):
    # This generator flattens the whole ZIP into one stream of raw POI documents.
    with zipfile.ZipFile(zip_path) as zf:
        for file_name in zf.namelist():
            if not file_name.startswith("objects/") or not file_name.endswith(".json"):
                continue
            for item in _iter_json_items_from_zip(zf, file_name):
                poi_id = item.get("@id")
                if not poi_id:
                    continue
                # `sort_keys=True` makes the hash stable even if JSON key order changes.
                content_hash = hashlib.sha256(
                    json.dumps(item, sort_keys=True, ensure_ascii=True).encode("utf-8")
                ).hexdigest()
                yield poi_id, item.get("dc:identifier"), item, file_name, content_hash


def _existing_hashes_for_ids(cursor, ids):
    if not ids:
        return {}
    # Fetch only the fields needed for change detection to keep Postgres reads light.
    cursor.execute(
        "SELECT id, content_hash FROM bronze_raw_poi WHERE id = ANY(%s)",
        (ids,),
    )
    return dict(cursor.fetchall())


def _flush_bronze_batch(cursor, pending_items, counts):
    if not pending_items:
        return

    # Compare the incoming batch against Postgres in one lookup so we can separate
    # new, changed, and unchanged documents before writing anything.
    existing_hashes = _existing_hashes_for_ids(
        cursor, [item["poi_id"] for item in pending_items]
    )
    rows_to_upsert = []

    for current in pending_items:
        existing_hash = existing_hashes.get(current["poi_id"])
        if existing_hash == current["content_hash"]:
            # Same id + same hash means the raw source record is unchanged.
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
        if existing_hash is None:
            counts["inserted"] += 1
        else:
            counts["updated"] += 1
        counts["total"] += 1

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
            SET source_identifier = EXCLUDED.source_identifier,
                raw_payload = EXCLUDED.raw_payload,
                source_file = EXCLUDED.source_file,
                content_hash = EXCLUDED.content_hash,
                updated_at = CURRENT_TIMESTAMP,
                ingested_at = CURRENT_TIMESTAMP
            WHERE bronze_raw_poi.content_hash IS DISTINCT FROM EXCLUDED.content_hash
            """,
            rows_to_upsert,
        )


def ingest_zip_to_postgres(conn, cursor, zip_path: str, batch_size: int = 1000):
    counts = {"total": 0, "inserted": 0, "updated": 0, "unchanged": 0}
    pending_items = []
    print("[Bronze API] Loading ZIP contents into Postgres bronze_raw_poi...")

    for poi_id, source_identifier, raw_payload, source_file, content_hash in _iter_zip_objects(zip_path):
        # Keep only a bounded number of documents in memory before flushing to Postgres.
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


def run_bronze_api_ingest():
    """Download the API ZIP and populate Postgres bronze_raw_poi."""
    print("[Pipeline] Bronze API ingest: start")
    config = load_config()
    zip_path = os.path.join(
        config["paths"]["raw_data_dir"],
        config["paths"].get("zip_output_file", "datatourisme_download.zip"),
    )

    try:
        with conn_env() as conn:
            with conn.cursor() as cursor:
                print("[Bronze API] Connected to Postgres")
                ensure_bronze_table(cursor)
                conn.commit()
                # Try the no-download path first; if it fails, the ZIP path still works.
                skip_download, freshness = _should_skip_download_from_catalog(
                    cursor,
                    config,
                )
                conn.commit()
                if skip_download:
                    print("[Bronze API] Bronze ingest skipped: API data is unchanged.")
                    print("[Pipeline] Bronze API ingest: done")
                    return

                zip_path = _download_zip(config["api"]["feed_url"], zip_path)
                # Bronze stops at raw storage; no normalization should happen in this stage.
                ingest_zip_to_postgres(
                    conn,
                    cursor,
                    zip_path,
                    batch_size=int(config.get("api", {}).get("batch_size", 1000)),
                )
                if freshness:
                    _save_feed_state(cursor, freshness, downloaded=True)
                    conn.commit()
    except Exception as exc:
        print(f"[Bronze API] Error during ingestion: {exc}")

    print("[Pipeline] Bronze API ingest: done")


if __name__ == "__main__":
    run_bronze_api_ingest()
