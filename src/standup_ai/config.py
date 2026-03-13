"""Load user configuration from ~/.standup.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_CONFIG_PATH = Path.home() / ".standup.yaml"


def load_config() -> dict[str, Any]:
    """Load config from ~/.standup.yaml. Returns empty dict if not found or invalid."""
    if not _CONFIG_PATH.exists():
        return {}
    try:
        import yaml  # type: ignore[import]
        with _CONFIG_PATH.open() as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def get_config_value(config: dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a value from config, returning default if not present."""
    return config.get(key, default)
