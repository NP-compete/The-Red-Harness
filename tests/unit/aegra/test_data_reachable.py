"""The agent must be able to read datasets uploaded to it."""

from __future__ import annotations

from pathlib import Path

from agent.src.agent.config import agent_config
from agent.src.infrastructure.backend import _readonly_root


def _published() -> Path:
    from agent.aegra.upload_routes import LIVE_DIR, _data_root

    return _data_root() / LIVE_DIR


def _route() -> Path:
    backend = agent_config.get_filesystem_config().backend
    routes = backend.routes or {}
    roots = getattr(backend, "roots", None) or {}
    return _readonly_root("/data/", str(routes["/data/"]), roots)


def test_the_agent_reads_where_uploads_publish():
    assert _route().resolve() == _published().resolve()


def test_the_directory_exists():
    assert _route().is_dir()
