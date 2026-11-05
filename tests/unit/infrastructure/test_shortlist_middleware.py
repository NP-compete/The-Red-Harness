"""Narrowing the tool list for one model call."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from agent.src.agent.config.middleware import ToolShortlistConfig
from agent.src.infrastructure.shortlist import ToolShortlistMiddleware


@dataclass
class _Tool:
    name: str


@dataclass
class _Request:
    tools: list[_Tool]
    state: dict[str, Any] = field(default_factory=dict)

    def override(self, **kwargs: Any) -> "_Request":
        return _Request(tools=kwargs.get("tools", self.tools), state=self.state)


def called(*names: str) -> dict[str, Any]:
    """A conversation in which these tools have already been called."""

    @dataclass
    class _Message:
        tool_calls: list[dict[str, str]]

    return {"messages": [_Message([{"name": n} for n in names])]}


def run(config, tools, state=None, **kwargs):
    seen: dict[str, Any] = {}

    def handler(request):
        seen["tools"] = [t.name for t in request.tools]
        return "answered"

    middleware = ToolShortlistMiddleware(config=config, **kwargs)
    middleware.wrap_model_call(_Request(tools, state or {}), handler)
    return seen["tools"]


TOOLS = [_Tool("read_file"), _Tool("gitlab_mr"), _Tool("atlan_search")]


class TestItOnlyActsWhenAsked:
    def test_the_default_sends_every_tool(self):
        assert run(ToolShortlistConfig(), TOOLS) == [t.name for t in TOOLS]

    def test_the_answer_still_comes_back(self):
        middleware = ToolShortlistMiddleware(config=ToolShortlistConfig())
        assert (
            middleware.wrap_model_call(_Request(TOOLS), lambda r: "answered")
            == "answered"
        )


class TestNarrowingOneCall:
    def test_an_undeclared_server_is_left_out(self):
        sent = run(
            ToolShortlistConfig(strategy="static"),
            TOOLS,
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "atlan_search" not in sent

    def test_the_agents_own_tools_are_still_sent(self):
        sent = run(
            ToolShortlistConfig(strategy="static"),
            TOOLS,
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "read_file" in sent


class TestWhatThisRunHasAlreadyUsed:
    def test_a_tool_already_called_survives(self):
        sent = run(
            ToolShortlistConfig(strategy="static"),
            TOOLS,
            state=called("atlan_search"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "atlan_search" in sent

    def test_a_tool_nobody_called_is_still_narrowed_away(self):
        sent = run(
            ToolShortlistConfig(strategy="static"),
            TOOLS,
            state=called("read_file"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "atlan_search" not in sent

    def test_a_conversation_with_no_history_narrows_normally(self):
        sent = run(
            ToolShortlistConfig(strategy="static"),
            TOOLS,
            state={"messages": []},
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "atlan_search" not in sent

    def test_a_state_it_cannot_read_narrows_rather_than_raising(self):
        sent = run(
            ToolShortlistConfig(strategy="static"),
            TOOLS,
            state={"messages": "not a list"},
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "gitlab_mr" in sent


class TestItIsAMiddlewareTheRuntimeRecognises:
    """A fake request is not the runtime."""

    def test_it_carries_a_name(self):
        middleware = ToolShortlistMiddleware(config=ToolShortlistConfig())
        assert getattr(middleware, "name", "")

    def test_it_is_the_kind_of_middleware_the_runtime_expects(self):
        from langchain.agents.middleware import AgentMiddleware

        assert isinstance(
            ToolShortlistMiddleware(config=ToolShortlistConfig()), AgentMiddleware
        )


class TestTheAsyncPathIsTheOneThatRuns:
    """The graph is async."""

    @pytest.mark.asyncio
    async def test_the_async_hook_narrows_too(self):
        seen = {}

        async def handler(request):
            seen["tools"] = [t.name for t in request.tools]
            return "answered"

        middleware = ToolShortlistMiddleware(
            config=ToolShortlistConfig(strategy="static"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        await middleware.awrap_model_call(_Request(TOOLS), handler)
        assert "atlan_search" not in seen["tools"]

    @pytest.mark.asyncio
    async def test_the_async_answer_comes_back(self):
        async def handler(request):
            return "answered"

        middleware = ToolShortlistMiddleware(config=ToolShortlistConfig())
        assert await middleware.awrap_model_call(_Request(TOOLS), handler) == "answered"


class TestAgainstADeploymentWithSeveralServers:
    """The case the feature exists for."""

    MANY = [
        _Tool(n)
        for n in (
            "read_file",
            "grep",
            "glob",
            "ls",
            "task",
            "gitlab_list_merge_requests",
            "gitlab_get_commit",
            "atlan_search",
            "atlan_lineage",
            "datadog_search_logs",
            "datadog_get_monitor",
            "unstructured_parse",
        )
    ]
    KNOWN = ("gitlab", "atlan", "datadog", "unstructured")

    def _sent(self, declared, **kwargs):
        return run(
            ToolShortlistConfig(strategy="static"),
            self.MANY,
            declared_servers=declared,
            known_servers=self.KNOWN,
            **kwargs,
        )

    def test_only_the_declared_servers_tools_are_advertised(self):
        sent = self._sent(("unstructured",))
        assert "gitlab_list_merge_requests" not in sent
        assert "unstructured_parse" in sent

    def test_the_agents_own_tools_always_survive(self):
        sent = self._sent(("unstructured",))
        assert {"read_file", "grep", "glob", "ls", "task"} <= set(sent)

    def test_it_drops_most_of_a_many_server_list(self):
        assert len(self._sent(("unstructured",))) == 6

    def test_declaring_more_servers_sends_more_tools(self):
        assert len(self._sent(("unstructured", "gitlab"))) > len(
            self._sent(("unstructured",))
        )

    def test_a_tool_used_earlier_in_the_run_survives_the_cut(self):
        sent = run(
            ToolShortlistConfig(strategy="static"),
            self.MANY,
            state=called("datadog_search_logs"),
            declared_servers=("unstructured",),
            known_servers=self.KNOWN,
        )
        assert "datadog_search_logs" in sent
