"""Shared YAML configuration for ArchiveLens command-line entry points."""

from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a YAML mapping")
    return {str(key).replace('-', '_'): value for key, value in data.items()}


def apply_config(args, config: dict[str, Any]):
    for key, value in config.items():
        if hasattr(args, key) and getattr(args, key) is None:
            setattr(args, key, value)
    return args
