"""Tests for the read-only admin config endpoint."""

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from agent.aegra.http_app import app

ADMIN_CLAIMS = {"sub": "admin-1", "preferred_username": "admin-1"}
USER_CLAIMS = {"sub": "user-1", "preferred_username": "user-1"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestAuthorization:
    def test_requires_a_bearer_token(self, client: TestClient):
        with patch("agent.aegra.auth.ENABLE_AUTH", True):
            assert client.get("/admin/config").status_code == 401

    def test_rejects_an_invalid_token(self, client: TestClient):
        import jwt

        with (
            patch("agent.aegra.auth.ENABLE_AUTH", True),
            patch(
                "agent.aegra.auth._decode_token",
                side_effect=jwt.PyJWTError("bad"),
            ),
        ):
            response = client.get(
                "/admin/config", headers={"Authorization": "Bearer nope"}
            )
        assert response.status_code == 401

    def test_unprivileged_role_is_forbidden(self, client: TestClient):
        """Config introspection is privileged — it names every tool and skill."""
        with (
            patch("agent.aegra.auth.ENABLE_AUTH", True),
            patch("agent.aegra.auth._decode_token", return_value=USER_CLAIMS),
            patch(
                "agent.src.ldap.resolve_user_role",
                return_value="users",
            ),
        ):
            response = client.get(
                "/admin/config", headers={"Authorization": "Bearer t"}
            )
        assert response.status_code == 403


class TestConfigReport:
    @staticmethod
    def _get(client: TestClient):
        with (
            patch("agent.aegra.auth.ENABLE_AUTH", True),
            patch("agent.aegra.auth._decode_token", return_value=ADMIN_CLAIMS),
            patch("agent.src.ldap.resolve_user_role", return_value="admins"),
        ):
            return client.get("/admin/config", headers={"Authorization": "Bearer t"})

    def test_reports_resolved_approval_decisions(self, client: TestClient):
        """The point of the endpoint: the effect of the globs, not the globs."""
        body = self._get(client).json()
        tools = body["approval"]["tools"]

        assert tools["ls"]["decision"] == "allow"
        assert tools["execute"]["decision"] == "ask"
        assert tools["execute"]["risk"] == "high"

    def test_reports_skills_and_their_paths(self, client: TestClient):
        skills = self._get(client).json()["skills"]
        assert skills, "config report lists no skills"
        assert all(isinstance(path, str) and path for path in skills.values())

    def test_reports_whether_opa_fails_open(self, client: TestClient):
        """An engine that is enabled but failing open enforces nothing."""
        engine = self._get(client).json()["policy_engine"]
        assert "opa_enabled" in engine
        assert "fail_open" in engine

    def test_reports_the_versions_this_build_reads(self, client: TestClient):
        schema = self._get(client).json()["schema"]
        assert schema["current"] >= schema["oldest_supported"]

    def test_reports_the_version_the_tree_declares(self, client: TestClient):
        from agent.src.agent.config.schema_version import CURRENT

        assert self._get(client).json()["schema"]["declared"] == CURRENT

    def test_says_whether_the_tree_is_on_the_old_end(self, client: TestClient):
        assert self._get(client).json()["schema"]["deprecated"] is False

    def test_does_not_leak_mcp_urls_or_credentials(self, client: TestClient):
        response = self._get(client)
        for server in response.json()["mcp_servers"].values():
            assert "url" not in server
            assert "auth_env_var" not in server
        assert "localhost:5001" not in response.text


class TestTheInboundDoor(TestConfigReport):
    """Whether another system may call this agent, and on what terms."""

    def test_it_says_whether_the_door_is_open(self, client: TestClient):
        assert self._get(client).json()["inbound"]["enabled"] is False

    def test_a_shut_door_has_no_limits_to_report(self, client: TestClient):
        assert self._get(client).json()["inbound"]["limits"] is None

    def test_it_counts_the_published_tools(self, client: TestClient):
        assert self._get(client).json()["inbound"]["published_tools"] == 0


class TestTheDocumentLibrary(TestConfigReport):
    """An interface cannot hide what it is not told about."""

    def test_it_says_whether_the_library_is_on(self, client: TestClient):
        from agent.src.agent.config.loader import agent_config

        # Mirrors the config rather than naming a default. These two
        # asserted the shipped tree shipped the library off; it ships
        # on, with a corpus, and the deployed agent answers from it.
        said = self._get(client).json()["knowledge"]["enabled"]
        assert said is agent_config.get_knowledge_config().enabled

    def test_a_library_that_is_on_reports_its_scopes(self, client: TestClient):
        from agent.src.agent.config.loader import agent_config

        said = self._get(client).json()["knowledge"]
        if not agent_config.get_knowledge_config().enabled:
            assert said["scopes"] == []
        else:
            assert said["scopes"], "an enabled library with no scopes reads as off"
