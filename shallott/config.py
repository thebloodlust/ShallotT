"""Configuration loader for ShallotT."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG: dict[str, Any] = {
    "ollama": {
        "host": "http://localhost:11434",
        "model": "gemma3:8b-instruct-q4_K_M",
        "timeout": 60,
        "verify_ssl": True,
    },
    "hotkeys": {
        "translate_clipboard": "<ctrl>+c+c",
        "translate_ocr": "<ctrl>+<f8>",
    },
    "translation": {
        "target_language": "en",
        "source_language": "auto",
    },
    "ocr": {
        "tesseract_cmd": None,
        "lang": "eng+fra+deu+spa+jpn+chi_sim",
    },
    "ui": {
        "overlay_duration": 8,
        "overlay_position": "bottom-right",
    },
}

_CONFIG_SEARCH_PATHS: list[Path] = [
    Path("config.json"),
    Path.home() / ".config" / "shallott" / "config.json",
    Path.home() / ".shallott.json",
]


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration, merging with defaults.

    Search order:
    1. Explicit *path* argument
    2. ``SHALLOTT_CONFIG`` environment variable
    3. ./config.json
    4. ~/.config/shallott/config.json
    5. ~/.shallott.json

    Returns a merged configuration dict (unknown keys are kept as-is).
    """
    cfg_path: Path | None = None

    if path is not None:
        cfg_path = Path(path)
    elif env_path := os.environ.get("SHALLOTT_CONFIG"):
        cfg_path = Path(env_path)
    else:
        for candidate in _CONFIG_SEARCH_PATHS:
            if candidate.exists():
                cfg_path = candidate
                break

    user_cfg: dict[str, Any] = {}
    if cfg_path is not None:
        with open(cfg_path, encoding="utf-8") as fh:
            user_cfg = json.load(fh)

    return _deep_merge(_DEFAULT_CONFIG, user_cfg)
