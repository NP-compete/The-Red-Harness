"""Reading a config file, with any edit laid over it."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_TREE = "config/agent"

_overlay: Any | None = None


def use_overlay(overlay: Any | None) -> None:
    """Set the overlay consulted by `effective_text`, or clear it."""
    global _overlay  # noqa: PLW0603
    _overlay = overlay


def overlay_key(path: Path) -> str | None:
    """The stable name this file is filed under, or `None`."""
    from agent.src.agent.config.paths import config_root

    try:
        root = Path(os.path.realpath(config_root()))
        inside = Path(os.path.realpath(path)).relative_to(root)
    except (ValueError, OSError):
        return None
    return f"{_TREE}/{inside.as_posix()}"


def overlay_generation() -> int:
    """How many edits this process has applied, for cache keying."""
    if _overlay is None:
        return 0
    return int(getattr(_overlay, "generation", 0))


def effective_text(path: Path) -> str:
    """What this config file says, after any edit to it."""
    if _overlay is not None:
        key = overlay_key(path)
        if key is not None:
            edited: str | None = _overlay.current(key)
            if edited is not None:
                return edited
    found: str = path.read_text()
    return found


def effective_exists(path: Path) -> bool:
    """Whether this config file exists, counting one an edit created."""
    if _overlay is not None:
        key = overlay_key(path)
        if key is not None and _overlay.current(key) is not None:
            return True
    return path.is_file()
