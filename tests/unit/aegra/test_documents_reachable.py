"""The agent must be able to read what was uploaded to it."""

from __future__ import annotations

from agent.aegra.document_routes import _root
from agent.src.agent.config import agent_config


def _documents_root():
    """Where the agent's `/documents/` route actually reads from."""
    from agent.src.infrastructure.backend import _readonly_root

    backend = agent_config.get_filesystem_config().backend
    routes = backend.routes or {}
    roots = getattr(backend, "roots", None) or {}
    return _readonly_root("/documents/", str(routes["/documents/"]), roots)


def test_the_route_names_a_path():
    assert str(_documents_root()), "/documents/ should resolve to a directory"


def test_the_agent_reads_where_uploads_are_written():
    assert _documents_root().resolve() == _root().resolve()


def test_the_directory_exists():
    assert _documents_root().is_dir()
