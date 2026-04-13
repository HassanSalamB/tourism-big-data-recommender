"""
End-to-end pipeline entrypoint.

Sequential stages:
  1. Bronze API ingest  — DATAtourisme API ZIP -> Postgres `bronze_raw_poi`
  2. Silver normalize   — Postgres bronze -> normalized Postgres silver tables + Parquet
  3. Gold (Postgres)    — Silver -> `gold_clusters` + itinerary sample
  4. Gold (Neo4j)       — Silver -> Neo4j graph
"""

from __future__ import annotations

import argparse
import os

from bronze.api_ingest import run_bronze_api_ingest
from gold.neo4j_graph_loader import run_neo4j_graph_load
from gold.postgres_warehouse import run_gold_postgres_dw
from silver.data_normalizer import run_silver_normalize
from utils.config import load_config


def _resolve_path(maybe_relative: str) -> str:
    # Config paths are stored relative to the project root unless already absolute.
    if not maybe_relative:
        return ""
    if os.path.isabs(maybe_relative):
        return maybe_relative
    root = os.path.join(os.path.dirname(__file__), "..")
    return os.path.normpath(os.path.join(root, maybe_relative))


def main():
    parser = argparse.ArgumentParser(
        description="DATAtourisme ETL pipeline (bronze -> silver -> gold)."
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip stage 1 (API bronze ingest).",
    )
    parser.add_argument(
        "--skip-silver",
        action="store_true",
        help="Skip stage 2 (silver normalize).",
    )
    parser.add_argument(
        "--skip-gold-pg",
        action="store_true",
        help="Skip stage 3 (Postgres gold / H3).",
    )
    parser.add_argument(
        "--skip-neo4j",
        action="store_true",
        help="Skip stage 4 (Neo4j graph build).",
    )
    parser.add_argument(
        "--silver-full",
        action="store_true",
        help="Silver: process all bronze records (disable test limit).",
    )
    args = parser.parse_args()

    # Postgres bronze is the source of truth; every later stage derives from it.
    cfg = load_config()
    # Docker and local runs may have different working directories, so resolve
    # config output paths relative to the project root before writing files.
    parquet_out = _resolve_path(
        cfg.get("db_paths", {}).get("parquet_output", "data/silver/parquet/places.parquet")
    )

    # Each stage is optional for debugging, but the default run executes the full flow.
    if not args.skip_api:
        run_bronze_api_ingest()

    if not args.skip_silver:
        run_silver_normalize(
            parquet_output=parquet_out,
            # Default is safe test mode; `--silver-full` intentionally processes all changed rows.
            test_mode=not args.silver_full,
            test_limit=5000,
            batch_size=int(cfg.get("api", {}).get("batch_size", 1000)),
        )

    if not args.skip_gold_pg:
        run_gold_postgres_dw()

    if not args.skip_neo4j:
        run_neo4j_graph_load()

    print("[Pipeline] All requested stages finished.")


if __name__ == "__main__":
    main()
