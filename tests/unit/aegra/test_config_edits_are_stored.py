"""An accepted edit is kept, and says how long it will last."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.aegra import config_editing_routes as surface


def _client(monkeypatch, *, mode="readwrite", store=None, role="ada") -> TestClient:
    monkeypatch.setenv("UI_CONFIG_MODE", mode)
    if store is None:
        monkeypatch.delenv("UI_CONFIG_STORE", raising=False)
    else:
        monkeypatch.setenv("UI_CONFIG_STORE", store)

    async def whoever(_request, developer_only=False):
        if role is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="not a developer")
        return role

    monkeypatch.setattr(surface, "check_ldap_role", whoever)
    surface.forget_overlay()
    app = FastAPI()
    surface.register(app)
    return TestClient(app)


PROMPT = "config/agent/PROMPT.md"
AGENT_YAML = "config/agent/runtime/agent.yaml"


def _nothing_overridden() -> bool:
    """No edit was recorded — whether or not a store was built."""
    overlay = surface.overlay_in_use()
    return overlay is None or overlay.overridden() == []


class TestWithNoStoreChosen:
    def test_an_edit_is_refused_rather_than_lost(self, monkeypatch):
        answer = _client(monkeypatch).put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert answer.status_code == 501

    def test_the_refusal_says_what_is_missing(self, monkeypatch):
        answer = _client(monkeypatch).put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert "store" in answer.json()["detail"].lower()


class TestWithTheInProcessStoreChosen:
    def test_an_edit_is_accepted(self, monkeypatch):
        answer = _client(monkeypatch, store="memory").put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert answer.status_code == 200

    def test_it_comes_back_with_its_version(self, monkeypatch):
        answer = _client(monkeypatch, store="memory").put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert answer.json()["version"] == 1

    def test_a_second_edit_is_a_second_version(self, monkeypatch):
        client = _client(monkeypatch, store="memory")
        client.put("/config/edit", json={"path": PROMPT, "content": "one"})
        answer = client.put("/config/edit", json={"path": PROMPT, "content": "two"})
        assert answer.json()["version"] == 2

    def test_it_says_the_edit_will_not_survive_a_restart(self, monkeypatch):
        answer = _client(monkeypatch, store="memory").put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert answer.json()["durable"] is False

    def test_the_edit_is_what_the_agent_then_reads(self, monkeypatch):
        from agent.src.agent.config.resolution import use_overlay

        client = _client(monkeypatch, store="memory")
        client.put("/config/edit", json={"path": PROMPT, "content": "the new wording"})

        overlay = surface.overlay_in_use()
        use_overlay(overlay)
        try:
            assert overlay.current(PROMPT) == "the new wording"
        finally:
            use_overlay(None)

    def test_who_made_the_edit_is_recorded(self, monkeypatch):
        client = _client(monkeypatch, store="memory", role="ada")
        client.put("/config/edit", json={"path": PROMPT, "content": "new"})
        assert surface.overlay_in_use().history(PROMPT)[-1].author == "ada"


class TestTheRulesStillHold:
    def test_a_path_outside_the_editable_set_is_refused(self, monkeypatch):
        answer = _client(monkeypatch, store="memory").put(
            "/config/edit", json={"path": "/etc/passwd", "content": "x"}
        )
        assert answer.status_code == 400

    def test_nothing_is_stored_for_a_refused_path(self, monkeypatch):
        client = _client(monkeypatch, store="memory")
        client.put("/config/edit", json={"path": "/etc/passwd", "content": "x"})
        assert _nothing_overridden()

    def test_a_caller_without_the_role_is_refused(self, monkeypatch):
        answer = _client(monkeypatch, store="memory", role=None).put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert answer.status_code == 403

    def test_nothing_is_stored_for_a_refused_caller(self, monkeypatch):
        client = _client(monkeypatch, store="memory", role=None)
        client.put("/config/edit", json={"path": PROMPT, "content": "new"})
        assert _nothing_overridden()

    def test_read_only_still_has_no_write_route(self, monkeypatch):
        answer = _client(monkeypatch, mode="readonly", store="memory").put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert answer.status_code == 404


class TestAnUnrecognisedStore:
    """`postgres` used to be in this list and is now a real store."""

    @pytest.mark.parametrize("named", ["redis", "disk", "yes"])
    def test_it_refuses_rather_than_guessing(self, monkeypatch, named):
        answer = _client(monkeypatch, store=named).put(
            "/config/edit", json={"path": PROMPT, "content": "new"}
        )
        assert answer.status_code == 501


class TestTheRouteCannotBypassValidation:
    """A second way in is the one without the checks."""

    def test_an_invalid_edit_is_refused_by_the_route(self, monkeypatch):
        answer = _client(monkeypatch, store="memory").put(
            "/config/edit",
            json={"path": AGENT_YAML, "content": "name: [unclosed\n"},
        )
        assert answer.status_code == 422

    def test_nothing_is_stored_for_an_invalid_edit(self, monkeypatch):
        client = _client(monkeypatch, store="memory")
        client.put(
            "/config/edit",
            json={"path": AGENT_YAML, "content": "name: [unclosed\n"},
        )
        assert _nothing_overridden()

    def test_the_route_goes_through_the_validating_path(self):
        import inspect

        source = inspect.getsource(surface)
        assert "apply_all" in source
        assert "overlay.apply(" not in source
