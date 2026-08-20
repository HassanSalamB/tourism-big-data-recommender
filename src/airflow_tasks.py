"""Small command entrypoints used by Airflow tasks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.bronze.bronze_loader import run_bronze_loader
from src.bronze.data_api import run_data_api_fetch
from src.utils.connections import conn_env
from src.utils.config import load_config


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return _project_root() / path


def _state_path() -> Path:
    return _project_root() / "data" / "airflow" / "bronze_fetch_state.json"


def _bronze_has_existing_rows() -> bool:
    try:
        with conn_env() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.bronze_raw_poi') IS NOT NULL")
                if not cursor.fetchone()[0]:
                    return False
                cursor.execute("SELECT EXISTS (SELECT 1 FROM bronze_raw_poi LIMIT 1)")
                return bool(cursor.fetchone()[0])
    except Exception as exc:
        print(f"[Airflow] Could not check existing bronze rows: {exc}")
        return False


def _zip_needs_load(zip_path: str) -> bool:
    metadata_file = f"{zip_path}.metadata.json"
    if not os.path.exists(metadata_file):
        return bool(os.path.exists(zip_path))
    try:
        metadata = json.loads(Path(metadata_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return bool(os.path.exists(zip_path))
    current_token_filename = metadata.get("token_filename")
    last_ingested_token_filename = metadata.get("last_ingested_token_filename")
    return bool(
        current_token_filename
        and current_token_filename != last_ingested_token_filename
    )


def bronze_download() -> None:
    cfg = load_config()
    result = run_data_api_fetch(cfg)
    if not result.get("ok"):
        error = result.get("error") or "Bronze ZIP download failed"
        if "status code 500" in error and _bronze_has_existing_rows():
            print(
                "[Airflow] Remote bronze feed returned 500, but existing bronze rows are present. "
                "Marking this run unchanged so downstream rebuild is skipped."
            )
        else:
            raise SystemExit(error)

    raw_dir = cfg["paths"]["raw_data_dir"]
    zip_name = cfg["paths"].get("zip_output_file", "datatourisme_download.zip")
    zip_path = result.get("zip_path") or str(_resolve_project_path(os.path.join(raw_dir, zip_name)))

    needs_load = bool(result.get("zip_path")) or _zip_needs_load(zip_path)
    state = {
        "zip_path": zip_path,
        "downloaded": result.get("zip_path") is not None,
        "needs_load": needs_load,
    }
    state_file = _state_path()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"[Airflow] Bronze download state written: {state_file}")
    print(f"[Airflow] Bronze ZIP path: {zip_path}")


def bronze_load() -> None:
    state_file = _state_path()
    if not state_file.exists():
        raise SystemExit(
            f"Missing bronze download state file: {state_file}. "
            "Run bronze_download_zip first."
        )

    state = json.loads(state_file.read_text(encoding="utf-8"))
    zip_path = state.get("zip_path")
    if not zip_path:
        raise SystemExit("Bronze download state did not contain zip_path")
    if not state.get("downloaded", True) and not state.get("needs_load", False):
        print("[Airflow] Bronze download reported unchanged remote ZIP. Skipping bronze load and downstream rebuild.")
        raise SystemExit(99)

    cfg = load_config()
    batch_size = int(
        os.getenv(
            "BRONZE_LOAD_BATCH_SIZE",
            str(cfg.get("api", {}).get("batch_size", 1000)),
        )
    )
    progress_interval = int(os.getenv("BRONZE_LOAD_PROGRESS_INTERVAL", "5000"))
    result = run_bronze_loader(
        zip_path,
        batch_size=batch_size,
        progress_interval=progress_interval,
    )
    if not result.get("ok"):
        raise SystemExit(result.get("error") or "Bronze load failed")

    print(f"[Airflow] Bronze change detection result: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Airflow task entrypoints.")
    parser.add_argument(
        "task",
        choices=["bronze-download", "bronze-load"],
    )
    args = parser.parse_args()

    if args.task == "bronze-download":
        bronze_download()
    elif args.task == "bronze-load":
        bronze_load()


if __name__ == "__main__":
    main()
