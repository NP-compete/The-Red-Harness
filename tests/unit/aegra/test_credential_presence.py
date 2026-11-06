"""Whether a server's credential is actually there."""

from __future__ import annotations

import pytest

from agent.src.security.credential_presence import (
    credential_state as _credential_state,
)


def _request() -> object:
    from unittest.mock import MagicMock

    request = MagicMock()
    request.headers = {}
    return request


class TestAServerUsingAKey:
    def test_a_set_variable_reads_as_present(self, monkeypatch):
        monkeypatch.setenv("JIRA_KEY", "a-key")
        found = _credential_state({"auth_mode": "api_key", "auth_env_var": "JIRA_KEY"})
        assert found == "set"

    def test_an_unset_variable_reads_as_missing(self, monkeypatch):
        monkeypatch.delenv("JIRA_KEY", raising=False)
        found = _credential_state({"auth_mode": "api_key", "auth_env_var": "JIRA_KEY"})
        assert found == "missing"

    def test_a_reference_that_resolves_reads_as_present(self, monkeypatch):
        monkeypatch.setenv("ELSEWHERE", "a-key")
        found = _credential_state(
            {"auth_mode": "api_key", "auth_env_var": "env:ELSEWHERE"}
        )
        assert found == "set"

    def test_a_reference_that_does_not_resolve_reads_as_missing(self, monkeypatch):
        monkeypatch.delenv("ELSEWHERE", raising=False)
        found = _credential_state(
            {"auth_mode": "api_key", "auth_env_var": "env:ELSEWHERE"}
        )
        assert found == "missing"

    def test_naming_no_variable_at_all_reads_as_missing(self):
        assert _credential_state({"auth_mode": "api_key"}) == "missing"


class TestAServerThatNeedsNoKeyOfItsOwn:
    @pytest.mark.parametrize("mode", ["sso", "oauth", "dcr", None])
    def test_it_is_not_reported_as_missing(self, mode):
        assert _credential_state({"auth_mode": mode}) == "not needed"


class TestTheValueNeverTravels:
    def test_only_the_three_words_are_ever_returned(self, monkeypatch):
        monkeypatch.setenv("JIRA_KEY", "super-secret-value")
        found = _credential_state({"auth_mode": "api_key", "auth_env_var": "JIRA_KEY"})
        assert found in {"set", "missing", "not needed"}

    def test_the_variable_name_is_not_returned_either(self, monkeypatch):
        monkeypatch.setenv("JIRA_KEY", "super-secret-value")
        found = _credential_state({"auth_mode": "api_key", "auth_env_var": "JIRA_KEY"})
        assert "JIRA_KEY" not in found


class TestItNeverBreaksThePage:
    def test_a_shape_it_cannot_read_does_not_raise(self):
        assert _credential_state("not a mapping") == "not needed"

    def test_nothing_at_all_does_not_raise(self):
        assert _credential_state(None) == "not needed"


class TestItIsOnTheSurface:
    def test_each_server_reports_it(self):
        import inspect

        from agent.aegra import admin_routes

        assert '"credential": credential_state(cfg)' in inspect.getsource(admin_routes)

    def test_the_variable_is_still_omitted(self):
        import inspect

        from agent.aegra import admin_routes

        source = inspect.getsource(admin_routes)
        assert '"auth_env_var": cfg' not in source


class TestItReachesTheListPeopleActuallyRead:
    """The server list in settings, not only the admin summary."""

    @staticmethod
    async def _listing(servers):
        import json
        from unittest.mock import AsyncMock, MagicMock, patch

        from agent.aegra import mcp_routes

        config = MagicMock()
        config.get_mcp_servers.return_value = servers
        with (
            patch("agent.src.agent.config.agent_config", config),
            patch.object(
                mcp_routes, "_authenticated_user_id", new=AsyncMock(return_value="u1")
            ),
        ):
            response = await mcp_routes.mcp_servers(_request())
        return {row["name"]: row for row in json.loads(response.body)["servers"]}

    @pytest.mark.asyncio
    async def test_a_server_whose_key_is_unset_says_so(self, monkeypatch):
        monkeypatch.delenv("JIRA_KEY", raising=False)
        rows = await self._listing(
            {"jira": {"auth_mode": "api_key", "auth_env_var": "JIRA_KEY"}}
        )
        assert rows["jira"]["credential"] == "missing"

    @pytest.mark.asyncio
    async def test_a_server_whose_key_is_set_says_so(self, monkeypatch):
        monkeypatch.setenv("JIRA_KEY", "a-key")
        rows = await self._listing(
            {"jira": {"auth_mode": "api_key", "auth_env_var": "JIRA_KEY"}}
        )
        assert rows["jira"]["credential"] == "set"

    @pytest.mark.asyncio
    async def test_a_server_signing_people_in_needs_none(self):
        rows = await self._listing({"jira": {"auth_mode": "dcr"}})
        assert rows["jira"]["credential"] == "not needed"

    @pytest.mark.asyncio
    async def test_the_variable_name_does_not_travel_with_it(self, monkeypatch):
        monkeypatch.setenv("JIRA_KEY", "super-secret-value")
        rows = await self._listing(
            {"jira": {"auth_mode": "api_key", "auth_env_var": "JIRA_KEY"}}
        )
        said = str(rows["jira"])
        assert "JIRA_KEY" not in said and "super-secret-value" not in said
