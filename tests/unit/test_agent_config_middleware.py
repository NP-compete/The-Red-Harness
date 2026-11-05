"""The agent cannot know which checkpoint is serving it."""

from __future__ import annotations

import pytest

from agent.src.infrastructure import middleware as mw


@pytest.fixture
def config(monkeypatch):
    """A fake agent_config with a settable orchestrator and subagents."""

    class _Cfg:
        orchestrator: dict = {"model": "gemini-3.8-flash"}
        subagents: dict = {}

        def get_orchestrator_config(self):
            return self.orchestrator

        def get_all_subagent_configs(self):
            return self.subagents

    cfg = _Cfg()
    import agent.src.agent.config as config_mod

    monkeypatch.setattr(config_mod, "agent_config", cfg)
    return cfg


class TestTheModelNameIsStated:
    def test_the_running_model_appears(self, config):
        assert "model: gemini-3.8-flash" in mw._agent_config_block()

    def test_it_says_to_prefer_this_over_recollection(self, config):
        assert "not from recollection" in mw._agent_config_block()

    def test_a_mapping_model_is_unwrapped(self, config):
        """`model:` is either a bare name or a mapping with one."""
        config.orchestrator = {"model": {"provider": "maas", "name": "granite-3.1-8b"}}
        assert "model: granite-3.1-8b" in mw._agent_config_block()


class TestItStaysOutOfTheCachedPrefixsWay:
    def test_identical_subagent_models_are_not_listed(self, config):
        """The `task` tool already describes the subagents. Repeating"""
        config.subagents = {
            "curator": {"model": "gemini-3.8-flash"},
            "investigator": {"model": "gemini-3.8-flash"},
        }
        assert "subagent models" not in mw._agent_config_block()

    def test_a_subagent_on_a_different_model_is_worth_the_tokens(self, config):
        config.subagents = {
            "curator": {"model": "gemini-3.8-flash"},
            "summariser": {"model": "claude-opus-5"},
        }
        block = mw._agent_config_block()
        assert "summariser: claude-opus-5" in block
        assert "curator" not in block

    def test_the_block_is_small(self, config):
        assert len(mw._agent_config_block()) < 400

    def test_nothing_user_or_turn_specific_leaks_in(self, config):
        """Anything varying per user or per turn would cost the whole"""
        first = mw._agent_config_block()
        assert first == mw._agent_config_block()


class TestItDegradesQuietly:
    def test_an_unreadable_config_yields_no_block(self, monkeypatch):
        class _Broken:
            def get_orchestrator_config(self):
                raise RuntimeError("config volume not mounted")

        import agent.src.agent.config as config_mod

        monkeypatch.setattr(config_mod, "agent_config", _Broken())
        assert mw._agent_config_block() == ""

    def test_no_model_configured_yields_no_block(self, config):
        config.orchestrator = {}
        assert mw._agent_config_block() == ""

    def test_the_middleware_is_absent_when_there_is_nothing_to_say(self, config):
        config.orchestrator = {}
        assert mw.build_agent_config_middleware() is None
