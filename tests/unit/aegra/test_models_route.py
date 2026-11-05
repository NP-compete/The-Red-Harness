"""The /models introspection route."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import agent.aegra.skill_routes as sr


class TestProviderOf:
    @pytest.mark.parametrize(
        ("model", "provider"),
        [
            ("gemini-3.5-flash", "google-vertex"),
            ("claude-sonnet-4", "anthropic-vertex"),
            ("gpt-4o", "openai"),
            ("o3-mini", "openai"),
            ("mock-model", "openai-compatible"),
            ("", "unknown"),
        ],
    )
    def test_resolves_by_prefix(self, model, provider):
        assert sr._provider_of(model) == provider


def _config(orchestrator=None, subagents=None):
    cfg = MagicMock()
    cfg.get_orchestrator_config.return_value = {"model": orchestrator}
    cfg.get_all_subagent_configs.return_value = subagents or {}
    return cfg


class TestListModels:
    @pytest.mark.asyncio
    async def test_reports_the_orchestrator(self):
        with patch("agent.src.agent.config.agent_config", _config("gemini-3.5-flash")):
            body = await sr.list_models()

        assert body["models"][0] == {
            "role": "orchestrator",
            "name": "gemini-3.5-flash",
            "provider": "google-vertex",
            "used_by": "The agent itself — every turn that is not delegated.",
        }

    @pytest.mark.asyncio
    async def test_unwraps_a_model_mapping(self):
        with patch(
            "agent.src.agent.config.agent_config",
            _config({"name": "claude-sonnet-4"}),
        ):
            body = await sr.list_models()
        assert body["models"][0]["name"] == "claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_distinguishes_a_chosen_model_from_an_inherited_one(self):
        subagents = {
            "curator": {"model": "gemini-3.5-flash-lite"},
            "investigator": {},
        }
        with patch(
            "agent.src.agent.config.agent_config",
            _config("gemini-3.5-pro", subagents),
        ):
            body = await sr.list_models()

        by_name = {m["used_by"]: m for m in body["models"] if m["role"] == "subagent"}
        assert by_name["curator"]["inherited"] is False
        assert by_name["investigator"]["inherited"] is True
        assert by_name["investigator"]["name"] == "gemini-3.5-pro"

    @pytest.mark.asyncio
    async def test_a_broken_config_costs_the_entry_not_the_route(self):
        cfg = MagicMock()
        cfg.get_orchestrator_config.side_effect = RuntimeError("bad yaml")
        cfg.get_all_subagent_configs.side_effect = RuntimeError("bad yaml")
        with patch("agent.src.agent.config.agent_config", cfg):
            body = await sr.list_models()

        assert body["models"] == []
        assert body["routing"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_reports_routing_tiers_when_enabled(self):
        from agent.src.routing.config import ModelTier, RouterConfig

        cfg = RouterConfig(
            enabled=True,
            tiers=[
                ModelTier(name="cheap", model="gemini-3.5-flash", criteria="simple"),
                ModelTier(name="strong", model="gemini-3.5-pro", criteria="hard"),
            ],
        )
        with (
            patch("agent.src.agent.config.agent_config", _config("gemini-3.5-pro")),
            patch("agent.src.routing.config.load_router_config", return_value=cfg),
        ):
            body = await sr.list_models()

        assert body["routing"]["enabled"] is True
        assert [t["tier"] for t in body["routing"]["tiers"]] == ["cheap", "strong"]
        assert body["routing"]["tiers"][0]["provider"] == "google-vertex"

    @pytest.mark.asyncio
    async def test_reports_no_endpoints_or_credentials(self):
        with patch("agent.src.agent.config.agent_config", _config("gemini-3.5-flash")):
            body = await sr.list_models()

        flat = str(body)
        for leak in ("http://", "https://", "project", "credential", "api_key"):
            assert leak not in flat.lower()


class TestHarnessProfileExclusions:
    """A profile can remove a tool for a given model."""

    @pytest.mark.asyncio
    async def test_reports_excluded_tools_for_the_model_that_loses_them(self):
        cfg = _config("gemini-3.8-flash")
        cfg.get_providers_config.return_value = SimpleNamespace(
            harness_profiles={
                "gemini-3.8-flash": SimpleNamespace(
                    excluded_tools=["write_file", "shell"],
                    excluded_middleware=["pii"],
                )
            }
        )
        with patch("agent.src.agent.config.agent_config", cfg):
            body = await sr.list_models()

        orchestrator = body["models"][0]
        assert orchestrator["excluded_tools"] == ["shell", "write_file"]
        assert orchestrator["excluded_middleware"] == ["pii"]

    @pytest.mark.asyncio
    async def test_an_empty_profile_adds_nothing(self):
        cfg = _config("gemini-3.8-flash")
        cfg.get_providers_config.return_value = SimpleNamespace(
            harness_profiles={
                "gemini-3.8-flash": SimpleNamespace(
                    excluded_tools=[], excluded_middleware=[]
                )
            }
        )
        with patch("agent.src.agent.config.agent_config", cfg):
            body = await sr.list_models()

        assert "excluded_tools" not in body["models"][0]

    @pytest.mark.asyncio
    async def test_unreadable_profiles_cost_the_detail_not_the_route(self):
        cfg = _config("gemini-3.8-flash")
        cfg.get_providers_config.side_effect = RuntimeError("bad yaml")
        with patch("agent.src.agent.config.agent_config", cfg):
            body = await sr.list_models()

        assert body["models"][0]["name"] == "gemini-3.8-flash"
