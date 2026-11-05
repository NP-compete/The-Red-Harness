"""A credential does not leave the run for an outside server."""

from unittest.mock import patch

import pytest

from agent.aegra.mcp_tool_auth import _secrets_in_args, wrap_mcp_tools_for_auth


class _Tool:
    def __init__(self):
        self.name = "atlan_fluent_search"
        self.func = None
        self.calls: list[dict] = []

        async def coroutine(**kwargs):
            self.calls.append(kwargs)
            return "ran"

        self.coroutine = coroutine

        async def ainvoke(_tool_input, _config=None, **_kwargs):
            return "ran"

        self.ainvoke = ainvoke


class TestSecretsInArgs:
    def test_finds_a_password_in_an_argument(self):
        assert _secrets_in_args({"query": "password: hunter2345"})

    def test_finds_one_nested_inside_a_structure(self):
        assert _secrets_in_args({"body": {"headers": ["Bearer abcdef1234567890"]}})

    def test_says_nothing_about_an_ordinary_query(self):
        assert _secrets_in_args({"query": "SELECT mail FROM people"}) == ""

    def test_says_nothing_about_an_empty_call(self):
        assert _secrets_in_args({}) == ""

    def test_names_what_it_found_without_repeating_it(self):
        found = _secrets_in_args({"query": "password: hunter2345"})
        assert "password" in found
        assert "hunter2345" not in found

    def test_ignores_a_placeholder_nobody_filled_in(self):
        assert _secrets_in_args({"query": "password: <your-password>"}) == ""


class TestWrappedTool:
    @pytest.mark.asyncio
    async def test_a_call_carrying_a_credential_does_not_run(self):
        tool = _Tool()
        wrapped = wrap_mcp_tools_for_auth([tool])[0]
        await wrapped.coroutine(query="password: hunter2345")
        assert tool.calls == []

    @pytest.mark.asyncio
    async def test_the_model_is_told_why(self):
        wrapped = wrap_mcp_tools_for_auth([_Tool()])[0]
        answer = await wrapped.coroutine(query="password: hunter2345")
        assert "credential" in str(answer).lower()

    @pytest.mark.asyncio
    async def test_the_credential_is_not_repeated_back(self):
        wrapped = wrap_mcp_tools_for_auth([_Tool()])[0]
        answer = await wrapped.coroutine(query="password: hunter2345")
        assert "hunter2345" not in str(answer)

    @pytest.mark.asyncio
    async def test_an_ordinary_call_still_runs(self):
        tool = _Tool()
        wrapped = wrap_mcp_tools_for_auth([tool])[0]
        await wrapped.coroutine(query="SELECT mail FROM people")
        assert tool.calls == [{"query": "SELECT mail FROM people"}]

    @pytest.mark.asyncio
    async def test_a_deployment_can_turn_the_check_off(self):
        tool = _Tool()
        wrapped = wrap_mcp_tools_for_auth([tool])[0]
        with patch("agent.aegra.mcp_tool_auth.settings.MCP_BLOCK_SECRETS", False):
            await wrapped.coroutine(query="password: hunter2345")
        assert tool.calls == [{"query": "password: hunter2345"}]
