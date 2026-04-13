"""Load project config and resolve paths from the organized `src/` package layout."""

from pathlib import Path
import yaml


def project_root() -> Path:
    # `utils/config.py` lives under `src/`, so the repo root is three levels up.
    return Path(__file__).resolve().parent.parent.parent


def load_config() -> dict:
    # Centralize config loading so every stage resolves the same `config.yaml`.
    path = project_root() / "config.yaml"
    # Keep config file IO here instead of duplicating path logic in each layer.
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
