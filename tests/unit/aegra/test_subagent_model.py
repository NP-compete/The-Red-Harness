"""Which model a subagent runs on, said in a way a reader can use."""

from __future__ import annotations

import pytest

from agent.aegra import skill_routes


@pytest.fixture
def listing(monkeypatch):
    async def run(configs: dict):
        from agent.src.agent.config import agent_config

        monkeypatch.setattr(agent_config, "get_all_subagent_configs", lambda: configs)
        monkeypatch.setattr(agent_config, "get_orchestrator_config", lambda: {})
        found = await skill_routes.list_subagents()
        return {agent["name"]: agent for agent in found["subagents"]}

    return run


@pytest.mark.asyncio
async def test_a_model_named_outright_is_reported_as_it_is(listing):
    agents = await listing({"curator": {"model": "gemini-3.8-flash"}})
    assert agents["curator"]["model"] == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_a_configured_model_reports_its_name_not_its_settings(listing):
    """`str()` on the config dict printed Python at the reader."""
    agents = await listing(
        {"curator": {"model": {"provider": "vertex", "name": "gemini-3.8-flash"}}}
    )
    assert agents["curator"]["model"] == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_the_provider_is_reported_beside_it(listing):
    agents = await listing(
        {"curator": {"model": {"provider": "vertex", "name": "gemini-3.8-flash"}}}
    )
    assert agents["curator"]["provider"] == "vertex"


@pytest.mark.asyncio
async def test_the_model_it_falls_back_to_is_named(listing):
    agents = await listing(
        {
            "curator": {
                "model": {
                    "provider": "vertex",
                    "name": "gemini-3.8-flash",
                    "fallback": {"provider": "vertex", "name": "gemini-3.8-pro"},
                }
            }
        }
    )
    assert agents["curator"]["fallback"] == "gemini-3.8-pro"


@pytest.mark.asyncio
async def test_no_fallback_is_reported_as_none(listing):
    agents = await listing({"curator": {"model": "gemini-3.8-flash"}})
    assert agents["curator"]["fallback"] == ""


@pytest.mark.asyncio
async def test_a_subagent_with_no_model_says_nothing_about_one(listing):
    agents = await listing({"curator": {}})
    assert agents["curator"]["model"] == ""
    assert agents["curator"]["provider"] == ""
