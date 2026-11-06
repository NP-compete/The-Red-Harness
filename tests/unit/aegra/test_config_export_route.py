"""Taking the configuration out, to reconcile and go back."""

from __future__ import annotations

import io
import tarfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.aegra import config_editing_routes as surface


def _client(monkeypatch, mode: str) -> TestClient:
    monkeypatch.setenv("UI_CONFIG_MODE", mode)
    monkeypatch.delenv("UI_CONFIG_STORE", raising=False)

    async def a_developer(_request, developer_only=False):
        return "ada"

    monkeypatch.setattr(surface, "check_ldap_role", a_developer)
    surface.forget_overlay()
    app = FastAPI()
    surface.register(app)
    return TestClient(app)


def _members(body: bytes) -> dict[str, str]:
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
        return {
            member.name: archive.extractfile(member).read().decode()
            for member in archive.getmembers()
            if member.isfile()
        }


@pytest.mark.parametrize("mode", ["readonly", "readwrite"])
def test_the_export_is_available_in_either_mode(monkeypatch, mode):
    assert _client(monkeypatch, mode).get("/config/export").status_code == 200


def test_it_is_an_archive(monkeypatch):
    answer = _client(monkeypatch, "readonly").get("/config/export")
    assert "gzip" in answer.headers["content-type"] or answer.headers[
        "content-type"
    ].startswith("application/")
    assert _members(answer.content)


def test_it_carries_the_tree_in_the_repositorys_layout(monkeypatch):
    held = _members(_client(monkeypatch, "readonly").get("/config/export").content)
    assert any(name.startswith("config/agent/") for name in held)
    assert "config/agent/PROMPT.md" in held


def test_it_offers_itself_as_a_file(monkeypatch):
    answer = _client(monkeypatch, "readonly").get("/config/export")
    assert "attachment" in answer.headers.get("content-disposition", "")


def test_the_contents_are_what_the_agent_reads(monkeypatch):
    from agent.src.agent.config.export import effective_tree

    held = _members(_client(monkeypatch, "readonly").get("/config/export").content)
    assert held == effective_tree()
