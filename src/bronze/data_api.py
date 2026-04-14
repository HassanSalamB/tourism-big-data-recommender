"""
Bronze API utilities: fetch DATAtourisme ZIP files and manage local ZIP metadata.
"""

from __future__ import annotations

import json
import os
import time
import zipfile
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from utils.config import load_config

load_dotenv()

API_TOKEN = os.getenv("DATATOURISME_TOKEN")


def run_data_api_fetch(config: dict) -> dict:
    """Fetch ZIP from API and return local path + status."""
    print("[Pipeline] Bronze API fetch: start")
    zip_path = os.path.join(
        config["paths"]["raw_data_dir"],
        config["paths"].get("zip_output_file", "datatourisme_download.zip"),
    )
    try:
        zip_path = download_zip(config["api"]["feed_url"], zip_path)
        print("[Pipeline] Bronze API fetch: done")
        # Contract for pipeline: {"ok": bool, "zip_path": str, "error"?: str}
        return {"ok": True, "zip_path": zip_path}
    except Exception as exc:
        print(f"[Bronze API] Error during fetch: {exc}")
        return {"ok": False, "zip_path": zip_path, "error": str(exc)}


def metadata_path(zip_path: str) -> str:
    return f"{zip_path}.metadata.json"


def has_local_zip_file(zip_path: str) -> bool:
    return os.path.exists(zip_path) and zipfile.is_zipfile(zip_path)


def is_valid_zip_file(zip_path: str) -> bool:
    if not has_local_zip_file(zip_path):
        return False
    try:
        with zipfile.ZipFile(zip_path) as zipped:
            return zipped.testzip() is None
    except (OSError, zipfile.BadZipFile):
        return False


def load_zip_metadata(zip_path: str) -> dict:
    metadata_file = metadata_path(zip_path)
    if not os.path.exists(metadata_file):
        return {}
    try:
        with open(metadata_file, encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except (OSError, json.JSONDecodeError):
        return {}


def save_zip_metadata_fields(zip_path: str, updates: dict) -> None:
    metadata = load_zip_metadata(zip_path)
    metadata.update({key: value for key, value in updates.items() if value is not None})
    with open(metadata_path(zip_path), "w", encoding="utf-8") as file_obj:
        json.dump(metadata, file_obj, indent=2)


def save_zip_metadata(zip_path: str, response, extra_fields: dict | None = None) -> None:
    metadata = load_zip_metadata(zip_path)
    updates = {
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
        "content_length": response.headers.get("Content-Length"),
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra_fields:
        updates.update(extra_fields)
    updates = {key: value for key, value in updates.items() if value}
    metadata.update(updates)
    with open(metadata_path(zip_path), "w", encoding="utf-8") as file_obj:
        json.dump(metadata, file_obj, indent=2)


def _download_headers(metadata: dict) -> dict:
    # `metadata` comes from `load_zip_metadata(zip_path)`.
    # If validators are present, send conditional headers to allow 304 responses.
    headers = {"Accept": "application/zip, application/octet-stream"}
    if metadata.get("etag"):
        headers["If-None-Match"] = metadata["etag"]
    if metadata.get("last_modified"):
        headers["If-Modified-Since"] = metadata["last_modified"]
    return headers


def _has_matching_validator(response, metadata: dict) -> bool:
    remote_etag = response.headers.get("ETag")
    if remote_etag and remote_etag == metadata.get("etag"):
        print("[Bronze API] Remote ETag unchanged. Reusing existing ZIP.")
        return True

    remote_last_modified = response.headers.get("Last-Modified")
    if remote_last_modified and remote_last_modified == metadata.get("last_modified"):
        print("[Bronze API] Remote Last-Modified unchanged. Reusing existing ZIP.")
        return True

    return False


def _extract_filename(content_disposition: str | None) -> str | None:
    if not content_disposition:
        return None
    lowered = content_disposition.lower()
    key = 'filename="'
    index = lowered.find(key)
    if index == -1:
        return None
    start = index + len(key)
    end = content_disposition.find('"', start)
    if end == -1:
        return None
    filename = content_disposition[start:end]
    return filename or None


def download_zip(url: str, zip_path: str) -> str:
    config = load_config()
    api_config = config.get("api", {})
    download_retries = int(api_config.get("download_retries", 3))
    wait_seconds = int(api_config.get("download_wait_seconds", 10))
    chunk_size = int(api_config.get("download_chunk_mb", 1)) * 1024 * 1024
    progress_log_seconds = int(api_config.get("progress_log_seconds", 5))
    token_url = f"{url}{API_TOKEN}" if API_TOKEN else url
    print(f"[Bronze API] Requesting ZIP from {token_url}...")

    for attempt in range(download_retries):
        metadata = load_zip_metadata(zip_path)
        headers = _download_headers(metadata)

        with requests.get(token_url, headers=headers, stream=True) as response:
            if response.status_code == 304:
                if is_valid_zip_file(zip_path):
                    print("[Bronze API] Remote ZIP not modified. Reusing existing ZIP.")
                    return zip_path
                raise ValueError("Remote ZIP was not modified, but local ZIP is missing/corrupt")

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()
                disposition_raw = response.headers.get("Content-Disposition")
                disposition = (disposition_raw or "").lower()
                remote_filename = _extract_filename(disposition_raw)
                # `previous_token_filename` is written in `save_zip_metadata(...)`
                # after a successful prior download.
                previous_token_filename = metadata.get("token_filename")
                if remote_filename:
                    print(
                        "[Bronze API] Token filename check: "
                        f"remote={remote_filename}, previous={previous_token_filename}"
                    )
                else:
                    print("[Bronze API] Token filename check: remote filename not provided by server.")

                if (
                    "zip" not in content_type
                    and "octet-stream" not in content_type
                    and ".zip" not in disposition
                ):
                    raise ValueError(f"Expected ZIP payload but received Content-Type={content_type!r}")

                if remote_filename and previous_token_filename == remote_filename:
                    # Server says filename is unchanged, so no need to download body.
                    print("[Bronze API] Token ZIP filename unchanged. Reusing existing ZIP.")
                    return zip_path

                if (
                    os.path.exists(zip_path)
                    and _has_matching_validator(response, metadata)
                    and has_local_zip_file(zip_path)
                ):
                    # Fallback skip path when filename is absent but validators match.
                    if remote_filename:
                        save_zip_metadata_fields(zip_path, {"token_filename": remote_filename})
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
                            if now - last_progress_log >= progress_log_seconds:
                                downloaded_mb = downloaded_bytes / (1024 * 1024)
                                print(f"[Bronze API] Downloaded {downloaded_mb:.1f} MB...")
                                last_progress_log = now
                if not is_valid_zip_file(zip_path):
                    print("[Bronze API] Downloaded file failed ZIP integrity check. Retrying download.")
                    try:
                        os.remove(zip_path)
                    except OSError:
                        pass
                    if attempt + 1 < download_retries:
                        time.sleep(wait_seconds)
                        continue
                    raise ValueError("Downloaded file is not a valid ZIP after retries")
                save_zip_metadata(
                    zip_path,
                    response,
                    {
                        "downloaded_at": datetime.now(timezone.utc).isoformat(),
                        "token_filename": remote_filename,
                    },
                )
                downloaded_mb = downloaded_bytes / (1024 * 1024)
                print(f"[Bronze API] ZIP download complete: {zip_path} ({downloaded_mb:.1f} MB)")
                return zip_path

            if response.status_code == 202:
                print(f"[Bronze API] Waiting for file (attempt {attempt + 1}/{download_retries})...")
                time.sleep(wait_seconds)
                continue

            raise ValueError(f"Download failed with status code {response.status_code}")

    raise ValueError("ZIP download failed after retries")
