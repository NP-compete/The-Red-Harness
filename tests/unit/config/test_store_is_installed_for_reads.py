"""The chosen store is installed where configuration is *read*."""

from __future__ import annotations

import pytest

from agent.aegra import config_editing_routes as routes
from agent.src.agent.config import resolution
from agent.src.agent.config.paths import config_root


@pytest.fixture(autouse=True)
def _clean():
    routes.forget_overlay()
    resolution.use_overlay(None)
    yield
    routes.forget_overlay()
    resolution.use_overlay(None)


def test_no_store_chosen_installs_nothing(monkeypatch):
    """A deployment that chose no store keys its reads as before."""
    monkeypatch.delenv(routes.STORE, raising=False)
    assert routes._store() is None
    assert resolution._overlay is None
    assert resolution.overlay_generation() == 0


def test_choosing_a_store_installs_it_for_reads(monkeypatch):
    monkeypatch.setenv(routes.STORE, "memory")
    store = routes._store()
    assert store is not None
    assert resolution._overlay is store, (
        "the store must be installed where configuration is read, not "
        "only where it is written"
    )


def test_an_edit_changes_what_a_config_read_returns(monkeypatch, tmp_path):
    """The whole point, end to end through the production path."""
    monkeypatch.setenv(routes.STORE, "memory")
    store = routes._store()

    target = config_root() / "runtime" / "pii.yaml"
    if not target.is_file():  # pragma: no cover - shipped tree has it
        pytest.skip("no pii.yaml in this tree")

    before = resolution.effective_text(target)
    key = resolution.overlay_key(target)
    assert key is not None

    store.apply(key, before + "\n# edited\n", author="test")

    after = resolution.effective_text(target)
    assert after.endswith("# edited\n")
    assert after != before
    assert target.read_text() == before, "the file on disk is untouched"


def test_registering_the_routes_installs_the_overlay(monkeypatch):
    """Before a request, not on the first one."""
    monkeypatch.setenv(routes.STORE, "memory")
    monkeypatch.setenv("UI_CONFIG_MODE", "readwrite")

    mounted = []

    class App:
        def include_router(self, router):
            mounted.append(router)

    routes.register(App())

    assert resolution._overlay is not None, (
        "the overlay must be in front of config reads when the app starts, "
        "not from the first request that happens to touch a config route"
    )


def test_an_edit_invalidates_the_loader_cache(monkeypatch):
    """An overlay edit changes no mtime, and the cache is keyed on mtimes."""
    from agent.src.agent.config.loader import agent_config

    monkeypatch.setenv(routes.STORE, "memory")
    store = routes._store()

    before = agent_config._disk_signature()
    target = config_root() / "runtime" / "agent.yaml"
    key = resolution.overlay_key(target)
    assert key is not None
    store.apply(key, resolution.effective_text(target) + "\n", author="test")

    assert agent_config._disk_signature() != before, (
        "an edit nobody can see is an edit that does nothing"
    )


def test_an_edit_can_create_a_config_file(monkeypatch):
    """The editor could change a file and not add one."""
    from agent.src.agent.config.resolution import effective_exists

    monkeypatch.setenv(routes.STORE, "memory")
    store = routes._store()

    absent = config_root() / "integrations" / "not-on-the-mount.yaml"
    assert not absent.is_file()
    assert not effective_exists(absent)

    key = resolution.overlay_key(absent)
    assert key is not None
    store.apply(key, "made: by an edit\n", author="test")

    assert effective_exists(absent), "an edit that creates a file creates a file"
    assert not absent.is_file(), "and does not write it to the mount"


def test_an_unrecognised_store_installs_nothing(monkeypatch):
    """Naming a store that does not exist must not be a silent memory"""
    monkeypatch.setenv(routes.STORE, "mongo")
    assert routes._store() is None
    assert resolution._overlay is None


def test_postgres_is_an_offered_store(monkeypatch):
    """The refusal message must name stores that exist."""
    import inspect

    from agent.aegra import config_editing_routes as routes

    source = inspect.getsource(routes)
    assert "not built yet" not in source
    assert "'postgres' to keep edits across restarts" in source
