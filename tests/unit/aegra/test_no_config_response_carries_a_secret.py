"""No route that describes the configuration hands back a secret."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

SECRET = "pl4nted-secret-value-nobody-should-see"


@pytest.fixture
def client(monkeypatch) -> TestClient:
    from agent.aegra.eval_routes import _require_developer
    from agent.aegra.http_app import app

    for name in (
        "SSO_CLIENT_SECRET",
        "TOKEN_SEALING_SECRET",
        "MCP_TOKEN_ENCRYPTION_KEY",
        "LANGFUSE_SECRET_KEY",
        "COOKIE_SIGN",
        "EVAL_INTERNAL_TOKEN",
    ):
        monkeypatch.setenv(name, SECRET)

    async def a_developer() -> str:
        return "ada"

    app.dependency_overrides[_require_developer] = a_developer
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _config_routes(client: TestClient) -> list[str]:
    """Every published path that describes configuration."""
    paths = client.app.openapi().get("paths", {})
    return sorted(
        path
        for path, verbs in paths.items()
        if "config" in path and "get" in {verb.lower() for verb in verbs}
    )


class TestTheSweepIsWorthRunning:
    def test_there_are_config_routes_to_check(self, client):
        assert len(_config_routes(client)) >= 3

    def test_none_of_them_takes_a_path_parameter_we_cannot_fill(self, client):
        assert all("{" not in path for path in _config_routes(client))

    def test_the_secret_is_actually_planted(self, client):
        import os

        assert os.environ["SSO_CLIENT_SECRET"] == SECRET


class TestNoConfigResponseCarriesASecret:
    def test_not_one_of_them(self, client):
        leaked: list[str] = []
        for path in _config_routes(client):
            answer = client.get(path)
            if answer.status_code >= 500:
                continue
            if SECRET in answer.text:
                leaked.append(path)
        assert leaked == [], (
            f"these answered with a secret value in the body: {leaked}. A "
            "configuration response may say that a credential is set; it may "
            "not say what it is."
        )

    def test_they_answer_at_all(self, client):
        answered = [
            path
            for path in _config_routes(client)
            if client.get(path).status_code < 400
        ]
        assert answered, "no config route answered, so nothing was checked"


class TestTheCheckCanFail:
    def test_a_route_that_does_leak_is_caught(self, client):
        """The sweep against a deliberately leaking route."""
        from fastapi import APIRouter

        leaky = APIRouter()

        @leaky.get("/config/deliberately-leaky")
        async def leaks() -> dict[str, str]:
            return {"client_secret": SECRET}

        client.app.include_router(leaky)
        client.app.openapi_schema = None
        try:
            found = [
                path
                for path in _config_routes(client)
                if SECRET in client.get(path).text
            ]
            assert found == ["/config/deliberately-leaky"]
        finally:
            client.app.router.routes = [
                route
                for route in client.app.router.routes
                if getattr(route, "path", "") != "/config/deliberately-leaky"
            ]
            client.app.openapi_schema = None

    def test_an_ordinary_body_is_not_flagged(self):
        assert SECRET not in '{"credential": "set"}'
