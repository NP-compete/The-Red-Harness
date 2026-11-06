"""Undoing an edit, in the two ways somebody means it."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.aegra import config_editing_routes as surface

PROMPT = "config/agent/PROMPT.md"


@pytest.fixture
def client(monkeypatch):
    def build(mode: str = "readwrite") -> TestClient:
        monkeypatch.setenv("UI_CONFIG_MODE", mode)
        monkeypatch.setenv("UI_CONFIG_STORE", "memory")

        async def a_developer(_request, developer_only=False):
            return "ada"

        monkeypatch.setattr(surface, "check_ldap_role", a_developer)
        surface.forget_overlay()
        app = FastAPI()
        surface.register(app)
        return TestClient(app)

    return build


def _edit(made: TestClient, content: str):
    answer = made.put("/config/edit", json={"path": PROMPT, "content": content})
    assert answer.status_code == 200, answer.text


class TestAdoptingTheBaseline:
    def test_the_path_stops_being_overridden(self, client):
        made = client()
        _edit(made, "mine\n")
        assert (
            made.post("/config/adopt-baseline", json={"path": PROMPT}).status_code
            == 200
        )
        assert made.get("/config/drift").json()["paths"] == []

    def test_it_leaves_a_version_behind(self, client):
        made = client()
        _edit(made, "mine\n")
        made.post("/config/adopt-baseline", json={"path": PROMPT})
        versions = made.get(f"/config/history?path={PROMPT}").json()["versions"]
        assert [one["version"] for one in versions] == [1, 2]

    def test_adopting_a_path_never_edited_changes_nothing(self, client):
        made = client()
        answer = made.post(
            "/config/adopt-baseline", json={"path": "config/agent/runtime/agent.yaml"}
        )
        assert answer.status_code in (200, 404)
        assert made.get("/config/drift").json()["paths"] == []


class TestRevertingToAVersion:
    def test_the_old_content_comes_back(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "two\n")
        assert (
            made.post("/config/revert", json={"path": PROMPT, "version": 1}).status_code
            == 200
        )
        found = made.get("/config/drift").json()["paths"][0]
        assert found["overlay"] == "one\n"

    def test_it_is_a_new_version_rather_than_a_deletion(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "two\n")
        made.post("/config/revert", json={"path": PROMPT, "version": 1})
        versions = made.get(f"/config/history?path={PROMPT}").json()["versions"]
        assert [one["version"] for one in versions] == [1, 2, 3]

    def test_the_version_that_was_undone_is_still_readable(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "a mistake\n")
        made.post("/config/revert", json={"path": PROMPT, "version": 1})
        versions = made.get(f"/config/history?path={PROMPT}").json()["versions"]
        assert versions[1]["content"] == "a mistake\n"

    def test_reverting_to_a_version_that_never_existed_is_refused(self, client):
        made = client()
        _edit(made, "one\n")
        answer = made.post("/config/revert", json={"path": PROMPT, "version": 9})
        assert answer.status_code == 404

    def test_the_refusal_names_the_path_and_the_version(self, client):
        made = client()
        _edit(made, "one\n")
        detail = made.post(
            "/config/revert", json={"path": PROMPT, "version": 9}
        ).json()["detail"]
        assert PROMPT in detail
        assert "9" in detail


class TestTheyAreWrites:
    def test_adopt_baseline_does_not_exist_in_read_only(self, client):
        answer = client(mode="readonly").post(
            "/config/adopt-baseline", json={"path": PROMPT}
        )
        assert answer.status_code == 404

    def test_revert_does_not_exist_in_read_only(self, client):
        answer = client(mode="readonly").post(
            "/config/revert", json={"path": PROMPT, "version": 1}
        )
        assert answer.status_code == 404


class TestTheyAreNotTheSameAct:
    def test_reverting_does_not_return_to_the_mounted_file(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "two\n")
        made.post("/config/revert", json={"path": PROMPT, "version": 1})
        assert made.get("/config/drift").json()["paths"], (
            "reverting removed the override entirely, which is what adopting "
            "the baseline does and not what reverting means"
        )

    def test_adopting_does_not_merely_rewind_one_step(self, client):
        made = client()
        _edit(made, "one\n")
        _edit(made, "two\n")
        made.post("/config/adopt-baseline", json={"path": PROMPT})
        assert made.get("/config/drift").json()["paths"] == []
