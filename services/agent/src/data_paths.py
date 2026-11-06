"""Where the agent's files live, wherever it happens to be running."""

from __future__ import annotations

from pathlib import Path

from agent._root import REPO_ROOT

_LOCAL_ROOT = REPO_ROOT / ".local"


def data_dir() -> Path:
    """The writable data mount, wherever the agent is running."""
    from agent.src.settings import settings

    return writable_dir(settings.DATA_PATH, "data")


def documents_dir() -> Path:
    """Where uploaded documents live, wherever the agent is running."""
    import os

    return writable_dir(
        os.environ.get("DOCUMENTS_PATH") or "/app/data/documents", "documents"
    )


def writable_dir(configured: str, name: str) -> Path:
    """The configured directory, or a local one when it cannot be made."""
    if configured:
        wanted = Path(configured)
        try:
            wanted.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        if wanted.is_dir():
            return wanted

    fallback = _LOCAL_ROOT / name
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback
