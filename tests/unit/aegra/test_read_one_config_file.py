"""Reading one configuration file as the agent now sees it."""

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


class TestReadingAFile:
    def test_the_text_comes_back(self, client):
        answer = client().get(f"/config/file?path={PROMPT}")
        assert answer.status_code == 200
        assert answer.json()["content"]

    def test_it_is_the_mounted_text_when_nothing_is_edited(self, client):
        from agent.src.agent.config.paths import config_root

        answer = client().get(f"/config/file?path={PROMPT}")
        assert answer.json()["content"] == (config_root() / "PROMPT.md").read_text()

    def test_it_is_the_edited_text_once_something_is_edited(self, client):
        made = client()
        made.put("/config/edit", json={"path": PROMPT, "content": "edited\n"})
        assert made.get(f"/config/file?path={PROMPT}").json()["content"] == "edited\n"

    def test_it_names_the_path_it_answered_about(self, client):
        assert client().get(f"/config/file?path={PROMPT}").json()["path"] == PROMPT


class TestOnlyEditablePaths:
    @pytest.mark.parametrize(
        "elsewhere",
        ["/etc/passwd", "config/agent/../../secrets.yaml", "runtime/pii.yaml"],
    )
    def test_anything_else_is_refused(self, client, elsewhere):
        answer = client().get(f"/config/file?path={elsewhere}")
        assert answer.status_code == 400

    def test_the_refusal_says_which_paths_are_editable(self, client):
        detail = client().get("/config/file?path=/etc/passwd").json()["detail"]
        assert "PROMPT.md" in detail


class TestAPathWithNoFileYet:
    def test_it_answers_with_nothing_rather_than_failing(self, client):
        answer = client().get("/config/file?path=config/agent/subagents/new.md")
        assert answer.status_code == 200
        assert answer.json()["content"] == ""
        assert answer.json()["exists"] is False


class TestReadingDoesNotNeedWriteMode:
    def test_a_read_only_deployment_can_still_read(self, client):
        answer = client(mode="readonly").get(f"/config/file?path={PROMPT}")
        assert answer.status_code == 200
