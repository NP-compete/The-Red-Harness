"""A read-only deployment has no write route, not a guarded one (CFG-10)."""

from __future__ import annotations

import pytest

from agent.aegra import config_editing_routes as routes

WRITERS = ("/edit", "/graph/edit", "/adopt-baseline", "/revert")

READERS = ("/editing", "/file", "/tree", "/settings", "/drift", "/history", "/export")


class Mounted:
    """Stands in for the app, and remembers what was mounted."""

    def __init__(self) -> None:
        self.paths: set[str] = set()

    def include_router(self, router) -> None:
        for route in router.routes:
            self.paths.add(route.path.removeprefix("/config"))


def _mount(mode: str, monkeypatch) -> set[str]:
    monkeypatch.setenv("UI_CONFIG_MODE", mode)
    monkeypatch.setenv(routes.STORE, "memory")
    app = Mounted()
    routes.register(app)
    return app.paths


@pytest.fixture(autouse=True)
def _clean():
    from agent.src.agent.config import resolution

    routes.forget_overlay()
    resolution.use_overlay(None)
    yield
    routes.forget_overlay()
    resolution.use_overlay(None)


class TestReadOnly:
    @pytest.mark.parametrize("writer", WRITERS)
    def test_the_write_routes_are_absent(self, writer, monkeypatch):
        mounted = _mount("readonly", monkeypatch)
        assert writer not in mounted, (
            f"{writer} is mounted in a read-only deployment. A guarded route "
            "is one authorisation mistake away from being a write; an absent "
            "one is not, and that is the only thing read-only promises."
        )

    @pytest.mark.parametrize("reader", READERS)
    def test_the_read_routes_are_still_there(self, reader, monkeypatch):
        mounted = _mount("readonly", monkeypatch)
        assert reader in mounted, (
            f"{reader} went with the writers. A deployment set back to "
            "read-only has not stopped being drifted — it has stopped being "
            "able to edit — and hiding the drift hides the problem at the "
            "moment somebody is resolving it."
        )

    @pytest.mark.parametrize("value", ["", "  ", "read-write", "rw", "yes"])
    def test_anything_that_is_not_readwrite_mounts_no_writer(self, value, monkeypatch):
        mounted = _mount(value, monkeypatch)
        assert not [one for one in WRITERS if one in mounted]


class TestReadWrite:
    @pytest.mark.parametrize("writer", WRITERS)
    def test_the_write_routes_are_there(self, writer, monkeypatch):
        assert writer in _mount("readwrite", monkeypatch)
