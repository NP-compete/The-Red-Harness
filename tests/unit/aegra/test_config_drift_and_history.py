"""Seeing what has drifted, and how it got that way."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.aegra import config_editing_routes as surface

PROMPT = "config/agent/PROMPT.md"


@pytest.fixture
def client(monkeypatch):
    def build(mode: str = "readwrite", store: str | None = "memory") -> TestClient:
        monkeypatch.setenv("UI_CONFIG_MODE", mode)
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

    return build


def _edit(client: TestClient, content: str, path: str = PROMPT):
    answer = client.put("/config/edit", json={"path": path, "content": content})
    assert answer.status_code == 200, answer.text
    return answer


class TestNothingHasDrifted:
    def test_the_drift_list_is_empty(self, client):
        assert client().get("/config/drift").json()["paths"] == []

    def test_it_says_so_rather_than_answering_with_nothing(self, client):
        body = client().get("/config/drift").json()
        assert "paths" in body


class TestSomethingHasDrifted:
    def test_the_path_is_listed(self, client):
        made = client()
        _edit(made, "the new wording\n")
        paths = made.get("/config/drift").json()["paths"]
        assert [one["path"] for one in paths] == [PROMPT]

    def test_it_shows_the_baseline_and_the_edit_side_by_side(self, client):
        made = client()
        _edit(made, "the new wording\n")
        found = made.get("/config/drift").json()["paths"][0]
        assert found["overlay"] == "the new wording\n"
        assert found["baseline"]
        assert found["baseline"] != found["overlay"]

    def test_it_names_who_and_when_and_which_version(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "two\n")
        found = made.get("/config/drift").json()["paths"][0]
        assert found["author"] == "ada"
        assert found["version"] == 2
        assert found["at"]

    def test_a_path_with_no_baseline_says_so(self, client):
        made = client()
        _edit(made, "# Invented\n", path="config/agent/subagents/invented.md")
        found = made.get("/config/drift").json()["paths"][0]
        assert found["baseline"] is None


class TestAnEditPutBackIsNotDrift:
    """Drift is a difference, not the existence of an overlay row."""

    def test_the_path_disappears_again(self, client):
        made = client()
        was = made.get("/config/file", params={"path": PROMPT}).json()["content"]
        _edit(made, "a change\n")
        assert made.get("/config/drift").json()["paths"]

        _edit(made, was)
        assert made.get("/config/drift").json()["paths"] == [], (
            "the file is back to what the image ships and is still reported as drifted"
        )

    def test_a_file_that_differs_is_still_reported(self, client):
        made = client()
        _edit(made, "a change\n")
        assert [one["path"] for one in made.get("/config/drift").json()["paths"]] == [
            PROMPT
        ]

    def test_an_added_file_is_still_reported(self, client):
        made = client()
        _edit(made, "# Invented\n", path="config/agent/subagents/invented.md")
        assert made.get("/config/drift").json()["paths"]


class TestSeeingTheDriftDoesNotNeedWriteMode:
    def test_the_drift_route_exists_in_read_only(self, client):
        assert client(mode="readonly").get("/config/drift").status_code == 200

    def test_the_history_route_exists_in_read_only(self, client):
        answer = client(mode="readonly").get(f"/config/history?path={PROMPT}")
        assert answer.status_code == 200


class TestTheHistoryOfOnePath:
    def test_every_version_is_listed_oldest_first(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "two\n")
        versions = made.get(f"/config/history?path={PROMPT}").json()["versions"]
        assert [one["version"] for one in versions] == [1, 2]

    def test_each_names_its_author_and_time(self, client):
        made = client()
        _edit(made, "one\n")
        found = made.get(f"/config/history?path={PROMPT}").json()["versions"][0]
        assert found["author"] == "ada"
        assert found["at"]

    def test_the_content_of_each_version_is_there(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "two\n")
        versions = made.get(f"/config/history?path={PROMPT}").json()["versions"]
        assert [one["content"] for one in versions] == ["one\n", "two\n"]

    def test_a_path_never_edited_has_an_empty_history(self, client):
        answer = client().get("/config/history?path=config/agent/runtime/agent.yaml")
        assert answer.json()["versions"] == []

    def test_an_adopted_baseline_shows_as_a_version_with_no_content(self, client):
        made = client()
        _edit(made, "mine\n")
        made.post("/config/adopt-baseline", json={"path": PROMPT})
        versions = made.get(f"/config/history?path={PROMPT}").json()["versions"]
        assert versions[-1]["content"] is None
