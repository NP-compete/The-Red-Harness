"""Letting another system call this agent, and whose authority it carries."""

from __future__ import annotations

import pytest

from agent.src.agent.config.inbound import (
    InboundMisconfigured,
    read_inbound,
)


class TestOffUntilAskedFor:
    def test_nothing_configured_is_off(self):
        assert read_inbound({}).enabled is False

    def test_an_empty_section_is_off(self):
        assert read_inbound({"mcp_server": {}}).enabled is False

    def test_off_needs_no_auth_mode(self):
        assert read_inbound({"mcp_server": {"enabled": False}}).enabled is False


class TestTurningItOn:
    def test_it_can_be_turned_on(self):
        raw = {"mcp_server": {"enabled": True, "auth": {"mode": "oauth"}}}
        assert read_inbound(raw).enabled is True

    def test_enabling_it_without_an_auth_mode_refuses_to_start(self):
        with pytest.raises(InboundMisconfigured, match="auth"):
            read_inbound({"mcp_server": {"enabled": True}})

    def test_the_refusal_says_what_to_set(self):
        with pytest.raises(InboundMisconfigured, match="oauth"):
            read_inbound({"mcp_server": {"enabled": True}})

    def test_a_service_identity_is_allowed(self):
        raw = {"mcp_server": {"enabled": True, "auth": {"mode": "service_token"}}}
        assert read_inbound(raw).auth_mode == "service_token"

    def test_an_unknown_auth_mode_refuses_to_start(self):
        raw = {"mcp_server": {"enabled": True, "auth": {"mode": "trust_me"}}}
        with pytest.raises(InboundMisconfigured, match="trust_me"):
            read_inbound(raw)


class TestTheDeputyCaseHasNoConfiguration:
    """The failure this whole boundary exists to prevent."""

    @pytest.mark.parametrize(
        "mode", ["agent", "own", "agent_credentials", "self", "service_account"]
    )
    def test_no_spelling_of_it_is_accepted(self, mode):
        raw = {"mcp_server": {"enabled": True, "auth": {"mode": mode}}}
        with pytest.raises(InboundMisconfigured):
            read_inbound(raw)

    def test_only_two_modes_exist_at_all(self):
        from agent.src.agent.config.inbound import AUTH_MODES

        assert set(AUTH_MODES) == {"oauth", "service_token"}

    def test_the_code_offers_no_way_to_use_the_agents_own_identity(self):
        import inspect

        from agent.src.agent.config import inbound

        source = inspect.getsource(inbound).lower()
        assert "agent_credentials" not in source.replace("# ", "")


class TestWhatIsPublished:
    def test_no_tools_are_published_by_default(self):
        raw = {"mcp_server": {"enabled": True, "auth": {"mode": "oauth"}}}
        assert read_inbound(raw).tools == ()

    def test_only_declared_tools_are_published(self):
        raw = {
            "mcp_server": {
                "enabled": True,
                "auth": {"mode": "oauth"},
                "tools": [
                    {"name": "ask", "description": "Ask a question", "scope": "read"}
                ],
            }
        }
        assert [t.name for t in read_inbound(raw).tools] == ["ask"]

    def test_a_tool_with_no_name_refuses_to_start(self):
        raw = {
            "mcp_server": {
                "enabled": True,
                "auth": {"mode": "oauth"},
                "tools": [{"description": "nameless"}],
            }
        }
        with pytest.raises(InboundMisconfigured, match="name"):
            read_inbound(raw)

    def test_a_tool_with_an_unknown_scope_refuses_to_start(self):
        raw = {
            "mcp_server": {
                "enabled": True,
                "auth": {"mode": "oauth"},
                "tools": [{"name": "ask", "scope": "everything"}],
            }
        }
        with pytest.raises(InboundMisconfigured, match="everything"):
            read_inbound(raw)

    def test_a_tool_defaults_to_the_narrower_scope(self):
        raw = {
            "mcp_server": {
                "enabled": True,
                "auth": {"mode": "oauth"},
                "tools": [{"name": "ask"}],
            }
        }
        assert read_inbound(raw).tools[0].scope == "read"


class TestTheShippedConfiguration:
    @staticmethod
    def _shipped():
        from pathlib import Path

        import yaml

        path = (
            Path(__file__).parents[3]
            / "config"
            / "agent"
            / "integrations"
            / "mcp_server.yaml"
        )
        if not path.is_file():
            return {}
        return yaml.safe_load(path.read_text()) or {}

    def test_it_ships_off(self):
        assert read_inbound(self._shipped()).enabled is False

    def test_it_is_readable(self):
        read_inbound(self._shipped())


class TestTheRemovalPlanIsWrittenNow:
    """Written while the reasoning is fresh, not at the end."""

    @staticmethod
    def _doc():
        from pathlib import Path

        return Path(__file__).parents[3] / "docs" / "guides" / "interop.md"

    def test_there_is_one(self):
        assert self._doc().is_file()

    def test_it_says_what_would_be_removed(self):
        said = self._doc().read_text().lower()
        assert "remove" in said or "delete" in said

    def test_it_says_what_would_be_kept(self):
        said = self._doc().read_text().lower()
        assert "keep" in said

    def test_it_says_why_this_was_built_over_the_protocol(self):
        assert "protocol" in self._doc().read_text().lower()


class TestWhatOneCallerMaySpend:
    """A deployment's model budget is shared, and an inbound caller"""

    @staticmethod
    def _on(limits=None):
        section = {"enabled": True, "auth": {"mode": "service_token"}}
        if limits is not None:
            section["limits"] = limits
        return read_inbound({"mcp_server": section})

    def test_no_limits_configured_means_none(self):
        assert self._on().limits is None

    def test_a_rate_is_read(self):
        assert self._on({"per_second": 2}).limits.per_second == 2

    def test_a_burst_is_read(self):
        assert self._on({"per_second": 2, "burst": 5}).limits.burst == 5

    def test_a_burst_defaults_to_the_rate(self):
        assert self._on({"per_second": 4}).limits.burst == 4

    def test_a_spend_cap_is_read(self):
        from decimal import Decimal

        found = self._on({"per_second": 2, "daily_spend": "5.00"})
        assert found.limits.daily_spend == Decimal("5.00")

    def test_a_spend_cap_is_read_as_a_decimal_not_a_float(self):
        from decimal import Decimal

        found = self._on({"per_second": 2, "daily_spend": 0.1})
        assert found.limits.daily_spend == Decimal("0.1")

    def test_no_spend_cap_means_no_spend_cap(self):
        assert self._on({"per_second": 2}).limits.daily_spend is None

    def test_a_cap_with_no_rate_is_still_limits(self):
        found = self._on({"daily_spend": "5.00"})
        assert found.limits.daily_spend is not None

    def test_a_nonsense_rate_refuses_to_start(self):
        with pytest.raises(InboundMisconfigured):
            self._on({"per_second": "quickly"})

    def test_a_nonsense_cap_refuses_to_start(self):
        with pytest.raises(InboundMisconfigured):
            self._on({"daily_spend": "lots"})

    def test_a_rate_of_zero_refuses_to_start(self):
        with pytest.raises(InboundMisconfigured):
            self._on({"per_second": 0})

    def test_the_refusal_names_the_setting(self):
        with pytest.raises(InboundMisconfigured, match="daily_spend"):
            self._on({"daily_spend": "lots"})

    def test_limits_are_ignored_while_the_door_is_shut(self):
        found = read_inbound({"mcp_server": {"limits": {"per_second": 1}}})
        assert found.limits is None


class TestTheLoaderReadsIt:
    """The gap: the model existed and nothing built one from the file."""

    @staticmethod
    def _load(tmp_path, text, monkeypatch):
        from agent.src.agent.config.loader import agent_config

        (tmp_path / "integrations").mkdir(parents=True, exist_ok=True)
        (tmp_path / "integrations" / "mcp_server.yaml").write_text(text)
        monkeypatch.setattr(agent_config, "_base_dir", tmp_path)
        return agent_config.get_inbound_config()

    def test_a_tree_with_no_file_is_off(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import agent_config

        monkeypatch.setattr(agent_config, "_base_dir", tmp_path)
        assert agent_config.get_inbound_config().enabled is False

    def test_the_shipped_file_is_off(self):
        from agent.src.agent.config.loader import agent_config

        assert agent_config.get_inbound_config().enabled is False

    def test_an_enabled_door_is_read(self, tmp_path, monkeypatch):
        text = "mcp_server:\n  enabled: true\n  auth:\n    mode: service_token\n"
        assert self._load(tmp_path, text, monkeypatch).enabled is True

    def test_limits_are_read(self, tmp_path, monkeypatch):
        text = (
            "mcp_server:\n  enabled: true\n  auth:\n    mode: service_token\n"
            "  limits:\n    per_second: 3\n    daily_spend: '2.50'\n"
        )
        from decimal import Decimal

        found = self._load(tmp_path, text, monkeypatch)
        assert found.limits.daily_spend == Decimal("2.50")

    def test_a_misconfigured_door_does_not_stop_everything_else(
        self, tmp_path, monkeypatch
    ):
        text = "mcp_server:\n  enabled: true\n"
        with pytest.raises(InboundMisconfigured):
            self._load(tmp_path, text, monkeypatch)
