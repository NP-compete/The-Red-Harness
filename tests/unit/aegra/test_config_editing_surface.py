"""The configuration write surface exists only where it is wanted."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.aegra import config_editing_routes as surface


def _app(mode: str | None, monkeypatch) -> TestClient:
    if mode is None:
        monkeypatch.delenv("UI_CONFIG_MODE", raising=False)
    else:
        monkeypatch.setenv("UI_CONFIG_MODE", mode)

    app = FastAPI()
    surface.register(app)
    return TestClient(app)


WRITES = {"put", "post", "patch", "delete"}


def _write_paths(client: TestClient) -> list[str]:
    """Every path this app exposes a write verb on."""
    paths = client.app.openapi().get("paths", {})
    return sorted(
        path for path, verbs in paths.items() if WRITES & {v.lower() for v in verbs}
    )


class TestADeploymentThatHasNotAskedForThis:
    def test_no_write_route_is_registered_at_all(self, monkeypatch):
        assert _write_paths(_app(None, monkeypatch)) == []

    def test_a_write_is_not_found_rather_than_refused(self, monkeypatch):
        answer = _app(None, monkeypatch).put(
            "/config/edit", json={"path": "config/agent/PROMPT.md", "content": "x"}
        )
        assert answer.status_code == 404

    def test_an_unrecognised_mode_is_treated_the_same(self, monkeypatch):
        assert _write_paths(_app("read-write", monkeypatch)) == []

    def test_reading_the_mode_still_works(self, monkeypatch):
        answer = _app(None, monkeypatch).get("/config/editing")
        assert answer.status_code == 200
        assert answer.json()["mode"] == "readonly"
        assert answer.json()["editable"] is False


class TestADeploymentThatHasAskedForIt:
    def test_the_write_surface_exists(self, monkeypatch):
        assert _write_paths(_app("readwrite", monkeypatch)) != []

    def test_the_mode_is_reported_as_editable(self, monkeypatch):
        answer = _app("readwrite", monkeypatch).get("/config/editing")
        assert answer.json()["mode"] == "readwrite"
        assert answer.json()["editable"] is True

    def test_it_says_which_paths_may_be_edited(self, monkeypatch):
        paths = _app("readwrite", monkeypatch).get("/config/editing").json()["paths"]
        assert paths
        assert any("PROMPT" in one for one in paths)


class TestTheSwitchIsNotPartOfTheSurface:
    @pytest.mark.parametrize("mode", [None, "readwrite"])
    def test_the_mode_itself_is_never_listed_as_editable(self, mode, monkeypatch):
        answer = _app(mode, monkeypatch).get("/config/editing")
        for path in answer.json()["paths"]:
            assert "ui_config_mode" not in path.lower()

    def test_a_deployment_cannot_make_itself_writable(self, monkeypatch):
        answer = _app(None, monkeypatch).put(
            "/config/edit", json={"path": "UI_CONFIG_MODE", "content": "readwrite"}
        )
        assert answer.status_code == 404


class TestTheCheckCanFail:
    def test_the_sweep_sees_a_write_route_when_there_is_one(self, monkeypatch):
        client = _app("readwrite", monkeypatch)
        assert any("/config" in path for path in _write_paths(client))

    def test_reading_is_not_counted_as_writing(self, monkeypatch):
        client = _app(None, monkeypatch)
        assert "/config/editing" not in _write_paths(client)
