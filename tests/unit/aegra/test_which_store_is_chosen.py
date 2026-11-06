"""Which store keeps an edit, and whether it says so truthfully."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.aegra import config_editing_routes as surface

PROMPT = "config/agent/PROMPT.md"


def _client(monkeypatch, store: str | None) -> TestClient:
    monkeypatch.setenv("UI_CONFIG_MODE", "readwrite")
    if store is None:
        monkeypatch.delenv("UI_CONFIG_STORE", raising=False)
    else:
        monkeypatch.setenv("UI_CONFIG_STORE", store)

    async def a_developer(_request, developer_only=False):
        return "ada"

    monkeypatch.setattr(surface, "check_ldap_role", a_developer)
    surface.forget_overlay()
    app = FastAPI()
    surface.register(app)
    return TestClient(app)


class TestTheInProcessStore:
    def test_it_is_chosen_by_name(self, monkeypatch):
        answer = _client(monkeypatch, "memory").put(
            "/config/edit", json={"path": PROMPT, "content": "x"}
        )
        assert answer.status_code == 200

    def test_it_admits_it_will_not_survive_a_restart(self, monkeypatch):
        answer = _client(monkeypatch, "memory").put(
            "/config/edit", json={"path": PROMPT, "content": "x"}
        )
        assert answer.json()["durable"] is False


class TestTheDurableStore:
    """Stood in for by the in-memory store, deliberately."""

    def _stood_in_for(self, monkeypatch):
        from agent.src.agent.config.overlay import InMemoryOverlay

        monkeypatch.setattr(
            surface, "_build_postgres_overlay", lambda: InMemoryOverlay()
        )

    def test_it_is_chosen_by_name(self, monkeypatch):
        self._stood_in_for(monkeypatch)
        answer = _client(monkeypatch, "postgres").put(
            "/config/edit", json={"path": PROMPT, "content": "x"}
        )
        assert answer.status_code == 200

    def test_it_says_the_edit_is_kept(self, monkeypatch):
        self._stood_in_for(monkeypatch)
        answer = _client(monkeypatch, "postgres").put(
            "/config/edit", json={"path": PROMPT, "content": "x"}
        )
        assert answer.json()["durable"] is True

    def test_a_database_it_cannot_reach_refuses_rather_than_falling_back(
        self, monkeypatch
    ):
        def explode():
            raise RuntimeError("no database")

        monkeypatch.setattr(surface, "_build_postgres_overlay", explode)
        answer = _client(monkeypatch, "postgres").put(
            "/config/edit", json={"path": PROMPT, "content": "x"}
        )
        assert answer.status_code == 501
        assert "database" in answer.json()["detail"].lower()


class TestNoStoreChosen:
    def test_an_edit_is_refused(self, monkeypatch):
        answer = _client(monkeypatch, None).put(
            "/config/edit", json={"path": PROMPT, "content": "x"}
        )
        assert answer.status_code == 501

    @pytest.mark.parametrize("named", ["redis", "disk", "yes", "true"])
    def test_an_unrecognised_name_is_refused_rather_than_guessed(
        self, monkeypatch, named
    ):
        answer = _client(monkeypatch, named).put(
            "/config/edit", json={"path": PROMPT, "content": "x"}
        )
        assert answer.status_code == 501
