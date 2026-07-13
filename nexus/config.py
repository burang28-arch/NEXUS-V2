from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_REQUIRED_TOP_LEVEL = {
    "project",
    "indicators",
    "entry",
    "scoring",
    "risk",
    "exit",
}


def load_config(path: Path) -> dict[str, Any]:
    """Load and minimally validate the strategy YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if not isinstance(config, dict):
        raise ValueError("Config root must be a YAML mapping.")

    missing = sorted(_REQUIRED_TOP_LEVEL.difference(config))
    if missing:
        raise ValueError(f"Config is missing sections: {', '.join(missing)}")

    return config
