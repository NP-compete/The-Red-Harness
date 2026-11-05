"""What a failed outside call tells the turn that made it."""

from __future__ import annotations

import pytest

from agent.aegra.mcp_tool_auth import _explain_failure, wrap_mcp_tools_for_auth


class _Tool:
    def __init__(self, raises: Exception):
        self.name = "atlan_fluent_search"
        self.func = None
        self._raises = raises

        async def coroutine(**_kwargs):
            raise self._raises

        self.coroutine = coroutine

        async def ainvoke(_tool_input, _config=None, **_kwargs):
            raise self._raises

        self.ainvoke = ainvoke


class TestExplainFailure:
    def test_names_the_tool_that_failed(self):
        assert "atlan_fluent_search" in _explain_failure(
            "atlan_fluent_search", TimeoutError("timed out")
        )

    def test_says_when_trying_again_is_worth_it(self):
        assert "try again" in _explain_failure("search", TimeoutError("timed out"))

    def test_does_not_promise_a_retry_will_help_when_it_will_not(self):
        assert "try again" not in _explain_failure("search", ValueError("bad argument"))

    def test_keeps_what_the_server_actually_said(self):
        """The turn needs the real message to work out what to do next."""
        assert "bad argument" in _explain_failure("search", ValueError("bad argument"))

    def test_carries_a_reference_an_operator_can_search_logs_for(self):
        explained = _explain_failure("search", ValueError("bad argument"))
        assert "reference" in explained.lower()

    def test_the_same_failure_gets_the_same_reference(self):
        first = _explain_failure("search", ValueError("bad argument"))
        second = _explain_failure("search", ValueError("bad argument"))
        assert first == second


class TestWrappedTool:
    @pytest.mark.asyncio
    async def test_a_timeout_comes_back_as_a_message_not_a_crash(self):
        wrapped = wrap_mcp_tools_for_auth([_Tool(TimeoutError("timed out"))])[0]
        answer = await wrapped.ainvoke({"id": "c1"})
        assert answer.status == "error"
        assert "try again" in answer.content
