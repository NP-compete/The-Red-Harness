"""The key that seals stored tokens is required, not advisory."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.aegra import startup
from agent.aegra.startup import MissingEncryptionKey, _check_mcp_encryption_key


def servers(**over):
    base = {"tracker": {"enabled": True, "auth_mode": "oauth"}}
    base.update(over)
    return base


def configured(mapping, key: str | None, dcr: bool = True):
    """Patch what the check reads: the servers, and the environment."""
    environment = {} if key is None else {"MCP_TOKEN_ENCRYPTION_KEY": key}
    agent_config = patch(
        "agent.src.agent.config.agent_config.get_mcp_servers",
        return_value=mapping,
    )
    settings = patch("agent.src.settings.settings.MCP_DCR_ENABLED", dcr)
    environ = patch.dict(startup.os.environ, environment, clear=True)
    return agent_config, settings, environ


def run(mapping, key: str | None, dcr: bool = True) -> None:
    a, s, e = configured(mapping, key, dcr)
    with a, s, e:
        _check_mcp_encryption_key()


class TestWhenTheKeyIsNeeded:
    def test_an_oauth_server_without_a_key_stops_startup(self):
        with pytest.raises(MissingEncryptionKey):
            run(servers(), key=None)

    def test_the_refusal_names_the_setting(self):
        with pytest.raises(MissingEncryptionKey, match="MCP_TOKEN_ENCRYPTION_KEY"):
            run(servers(), key=None)

    def test_the_refusal_names_the_server_that_needs_it(self):
        with pytest.raises(MissingEncryptionKey, match="tracker"):
            run(servers(), key=None)

    def test_a_key_that_is_only_whitespace_is_no_key(self):
        with pytest.raises(MissingEncryptionKey):
            run(servers(), key="   ")

    def test_a_dcr_server_needs_one_too(self):
        mapping = {"wiki": {"enabled": True, "auth_mode": "dcr"}}
        with pytest.raises(MissingEncryptionKey):
            run(mapping, key=None)


class TestWhenItIsNot:
    def test_a_key_that_is_set_is_enough(self):
        run(servers(), key="a-key")

    def test_a_deployment_with_no_oauth_needs_no_key(self):
        run({"docs": {"enabled": True, "auth_mode": "none"}}, key=None)

    def test_a_disabled_oauth_server_does_not_demand_one(self):
        mapping = {"tracker": {"enabled": False, "auth_mode": "oauth"}}
        run(mapping, key=None)

    def test_no_servers_at_all_needs_no_key(self):
        run({}, key=None)

    def test_dcr_turned_off_leaves_a_dcr_server_out_of_it(self):
        mapping = {"wiki": {"enabled": True, "auth_mode": "dcr"}}
        run(mapping, key=None, dcr=False)


class TestTheCheckItself:
    def test_a_check_that_cannot_run_is_not_silently_skipped(self):
        """Swallowing this put the deployment back where it started,"""
        with patch(
            "agent.src.agent.config.agent_config.get_mcp_servers",
            side_effect=RuntimeError("config unavailable"),
        ):
            with pytest.raises(Exception) as error:
                _check_mcp_encryption_key()
        assert not isinstance(error.value, AssertionError)
