"""How often each check has actually been run (E22-T4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

USAGE_FILE = "evals/usage.json"


def _path() -> Path:
    from agent.src.data_paths import data_dir

    return data_dir() / USAGE_FILE


def counts() -> dict[str, int]:
    """What has been run, and how often. Empty when nothing has."""
    path = _path()
    if not path.is_file():
        return {}
    try:
        found = json.loads(path.read_text())
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not read the check usage counts: %s", error)
        return {}
    if not isinstance(found, dict):
        return {}
    return {str(k): int(v) for k, v in found.items() if isinstance(v, int)}


def record(name: str) -> None:
    """Note that this check ran. Never raises."""
    if not name:
        return
    path = _path()
    try:
        found = counts()
        found[name] = found.get(name, 0) + 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(found, indent=2, sort_keys=True))
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not record that '%s' ran: %s", name, error)


def applied_to(registry: Any) -> dict[str, int]:
    """The declared checks, with the counts that outlived the process."""
    kept = counts()
    return {name: kept.get(name, 0) for name in registry.usage()}
