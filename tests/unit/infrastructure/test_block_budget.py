"""Catching a tool called in a loop without refusing a long answer."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from agent.src.agent.config.middleware import ToolCallLimitConfig
from agent.src.infrastructure.block_budget import spent_in_block


@dataclass
class _AI:
    tool_calls: list[dict] = field(default_factory=list)
    type: str = "ai"


@dataclass
class _Tool:
    name: str
    type: str = "tool"


def calls(*names: str) -> _AI:
    return _AI([{"name": n} for n in names])


class TestCountingOneBlock:
    def test_a_quiet_block_spends_nothing(self):
        assert spent_in_block([calls("read_file")], per_block=3) == set()

    def test_a_tool_at_its_limit_is_not_yet_over(self):
        block = [calls("grep", "grep", "grep")]
        assert spent_in_block(block, per_block=3) == set()

    def test_a_tool_past_its_limit_is_named(self):
        block = [calls("grep", "grep", "grep", "grep")]
        assert spent_in_block(block, per_block=3) == {"grep"}

    def test_other_tools_are_unaffected(self):
        block = [calls("grep", "grep", "grep", "grep", "read_file")]
        assert spent_in_block(block, per_block=3) == {"grep"}

    def test_two_tools_can_both_be_over(self):
        block = [calls(*(["grep"] * 4), *(["ls"] * 4))]
        assert spent_in_block(block, per_block=3) == {"grep", "ls"}


class TestWhereTheBlockBegins:
    def test_only_the_latest_model_turn_counts(self):
        history = [
            calls(*(["grep"] * 3)),
            _Tool("grep"),
            calls("grep"),
        ]
        assert spent_in_block(history, per_block=3) == set()

    def test_a_loop_inside_the_latest_turn_is_caught(self):
        history = [calls("grep"), _Tool("grep"), calls(*(["grep"] * 4))]
        assert spent_in_block(history, per_block=3) == {"grep"}


class TestWhenItDoesNotApply:
    def test_no_limit_means_no_ceiling(self):
        assert spent_in_block([calls(*(["grep"] * 50))], per_block=0) == set()

    def test_an_empty_conversation_spends_nothing(self):
        assert spent_in_block([], per_block=3) == set()

    def test_messages_it_cannot_read_spend_nothing(self):
        assert spent_in_block("not a list", per_block=3) == set()


class TestTheConfigCarriesTheNewScopes:
    def test_a_per_block_ceiling_is_configurable(self):
        assert ToolCallLimitConfig(per_block=5).per_block == 5

    def test_a_per_thread_ceiling_is_configurable(self):
        assert ToolCallLimitConfig(per_thread=900).per_thread == 900

    def test_what_happens_when_a_budget_is_spent_is_configurable(self):
        assert ToolCallLimitConfig(on_exceeded="error").on_exceeded == "error"

    def test_the_default_excludes_rather_than_failing_the_run(self):
        assert ToolCallLimitConfig().on_exceeded == "exclude"

    def test_an_existing_config_keeps_working_unchanged(self):
        existing = ToolCallLimitConfig(run_limit=200, per_tool={"grep": 6})
        assert existing.run_limit == 200 and existing.per_tool == {"grep": 6}


@dataclass
class _T:
    name: str


@dataclass
class _Request:
    tools: list
    state: dict = field(default_factory=dict)

    def override(self, **kwargs):
        return _Request(tools=kwargs.get("tools", self.tools), state=self.state)


def sent(config, tools, messages):
    from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

    seen = {}

    def handler(request):
        seen["tools"] = [t.name for t in request.tools]
        return "answered"

    BlockBudgetMiddleware(config=config).wrap_model_call(
        _Request(tools, {"messages": messages}), handler
    )
    return seen["tools"]


TOOLS = [_T("grep"), _T("read_file"), _T("ls")]


class TestWhatTheNextCallIsOffered:
    def test_a_looping_tool_is_taken_away(self):
        over = [calls(*(["grep"] * 4))]
        assert "grep" not in sent(ToolCallLimitConfig(per_block=3), TOOLS, over)

    def test_the_other_tools_are_left_alone(self):
        over = [calls(*(["grep"] * 4))]
        assert {"read_file", "ls"} <= set(
            sent(ToolCallLimitConfig(per_block=3), TOOLS, over)
        )

    def test_a_tool_within_budget_keeps_its_place(self):
        fine = [calls("grep", "grep")]
        assert "grep" in sent(ToolCallLimitConfig(per_block=3), TOOLS, fine)

    def test_no_ceiling_takes_nothing_away(self):
        over = [calls(*(["grep"] * 40))]
        assert "grep" in sent(ToolCallLimitConfig(), TOOLS, over)

    def test_the_run_carries_on_rather_than_failing(self):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        over = [calls(*(["grep"] * 4))]
        answer = BlockBudgetMiddleware(
            config=ToolCallLimitConfig(per_block=3)
        ).wrap_model_call(_Request(TOOLS, {"messages": over}), lambda r: "answered")
        assert answer == "answered"


class TestItIsAMiddlewareTheRuntimeRecognises:
    def test_it_carries_a_name(self):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        assert getattr(BlockBudgetMiddleware(config=ToolCallLimitConfig()), "name", "")

    def test_it_is_the_kind_the_runtime_expects(self):
        from langchain.agents.middleware import AgentMiddleware

        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        assert isinstance(
            BlockBudgetMiddleware(config=ToolCallLimitConfig()), AgentMiddleware
        )

    async def test_the_async_hook_excludes_too(self):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        seen = {}

        async def handler(request):
            seen["tools"] = [t.name for t in request.tools]
            return "answered"

        over = [calls(*(["grep"] * 4))]
        await BlockBudgetMiddleware(
            config=ToolCallLimitConfig(per_block=3)
        ).awrap_model_call(_Request(TOOLS, {"messages": over}), handler)
        assert "grep" not in seen["tools"]


@dataclass
class _FullRequest:
    tools: list
    messages: list = field(default_factory=list)
    state: dict = field(default_factory=dict)

    def override(self, **kwargs):
        return _FullRequest(
            tools=kwargs.get("tools", self.tools),
            messages=kwargs.get("messages", self.messages),
            state=self.state,
        )


class TestTellingTheModelWhy:
    """A tool that simply disappears is a tool the model will try"""

    def _messages(self, per_block=2):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        seen = {}

        def handler(request):
            seen["messages"] = list(request.messages)
            return "answered"

        over = [calls(*(["grep"] * 4))]
        BlockBudgetMiddleware(
            config=ToolCallLimitConfig(per_block=per_block)
        ).wrap_model_call(
            _FullRequest(TOOLS, messages=[calls("grep")], state={"messages": over}),
            handler,
        )
        return seen["messages"]

    def test_the_model_is_told_something(self):
        assert len(self._messages()) > 1

    def test_it_names_the_tool(self):
        said = " ".join(str(getattr(m, "content", m)) for m in self._messages())
        assert "grep" in said

    def test_it_says_which_scope_was_spent(self):
        said = " ".join(str(getattr(m, "content", m)) for m in self._messages())
        assert "block" in said.lower()

    def test_it_says_the_run_can_continue(self):
        said = " ".join(str(getattr(m, "content", m)) for m in self._messages())
        assert "answer" in said.lower()

    def test_nothing_is_said_when_no_budget_is_spent(self):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        seen = {}

        def handler(request):
            seen["messages"] = list(request.messages)
            return "answered"

        BlockBudgetMiddleware(config=ToolCallLimitConfig(per_block=9)).wrap_model_call(
            _FullRequest(
                TOOLS, messages=[calls("grep")], state={"messages": [calls("grep")]}
            ),
            handler,
        )
        assert len(seen["messages"]) == 1


class TestAcrossAWholeConversation:
    """The scope neither other cap can express."""

    def _over(self, per_thread, history):
        from agent.src.infrastructure.block_budget import spent_in_thread

        return spent_in_thread(history, per_thread=per_thread)

    def test_a_short_conversation_spends_nothing(self):
        assert self._over(10, [calls("grep"), _Tool("grep")]) == set()

    def test_calls_add_up_across_turns(self):
        history = []
        for _ in range(6):
            history += [calls("grep"), _Tool("grep")]
        assert self._over(5, history) == {"grep"}

    def test_a_tool_at_the_limit_is_not_yet_over(self):
        history = []
        for _ in range(5):
            history += [calls("grep"), _Tool("grep")]
        assert self._over(5, history) == set()

    def test_each_tool_has_its_own_allowance(self):
        history = [calls(*(["grep"] * 6)), calls("ls")]
        assert self._over(5, history) == {"grep"}

    def test_no_ceiling_means_no_counting(self):
        history = [calls(*(["grep"] * 90))]
        assert self._over(0, history) == set()

    def test_a_history_it_cannot_read_spends_nothing(self):
        assert self._over(5, "not a list") == set()


class TestTheThreadCeilingIsEnforced:
    def test_a_tool_over_its_thread_allowance_is_taken_away(self):
        history = [calls(*(["grep"] * 6))]
        assert "grep" not in sent(ToolCallLimitConfig(per_thread=5), TOOLS, history)

    def test_the_block_ceiling_still_applies_on_its_own(self):
        over_block = [calls(*(["grep"] * 4))]
        assert "grep" not in sent(ToolCallLimitConfig(per_block=3), TOOLS, over_block)

    def test_a_conversation_inside_both_allowances_keeps_its_tools(self):
        fine = [calls("grep"), _Tool("grep"), calls("grep")]
        config = ToolCallLimitConfig(per_block=3, per_thread=10)
        assert "grep" in sent(config, TOOLS, fine)


class _Reply:
    """Stands in for what the model call returns."""

    def __init__(self):
        self.result = [SimpleNamespace(additional_kwargs={})]


def answered(config, messages):
    """The reply, after the middleware has had its say."""
    from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

    reply = _Reply()
    BlockBudgetMiddleware(config=config).wrap_model_call(
        _Request(TOOLS, {"messages": messages}), lambda r: reply
    )
    return reply.result[0].additional_kwargs.get("answer_notes", {}).get("budget")


class TestTheReaderIsToldToo:
    """An answer written without a tool looks shallow for no reason."""

    def test_nothing_is_claimed_when_nothing_was_withheld(self):
        assert answered(ToolCallLimitConfig(per_block=3), [calls("grep")]) is None

    def test_a_withheld_tool_is_recorded_on_the_answer(self):
        note = answered(ToolCallLimitConfig(per_block=3), [calls(*(["grep"] * 4))])
        assert note is not None

    def test_the_tool_is_named(self):
        note = answered(ToolCallLimitConfig(per_block=3), [calls(*(["grep"] * 4))])
        assert note["withheld"] == ["grep"]

    def test_the_scope_and_its_ceiling_are_named(self):
        note = answered(ToolCallLimitConfig(per_block=3), [calls(*(["grep"] * 4))])
        assert note["scope"] == "block"
        assert note["limit"] == 3

    def test_a_conversation_ceiling_is_named_as_such(self):
        history = [calls(*(["grep"] * 6))]
        note = answered(ToolCallLimitConfig(per_thread=5), history)
        assert note["scope"] == "conversation"

    def test_a_reply_it_cannot_write_on_is_left_alone(self):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        over = [calls(*(["grep"] * 4))]
        answer = BlockBudgetMiddleware(
            config=ToolCallLimitConfig(per_block=3)
        ).wrap_model_call(
            _Request(TOOLS, {"messages": over}), lambda r: "a bare string"
        )
        assert answer == "a bare string"

    async def test_the_async_path_records_it_too(self):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        reply = _Reply()

        async def handler(request):
            return reply

        await BlockBudgetMiddleware(
            config=ToolCallLimitConfig(per_block=3)
        ).awrap_model_call(
            _Request(TOOLS, {"messages": [calls(*(["grep"] * 4))]}), handler
        )
        notes = reply.result[0].additional_kwargs["answer_notes"]
        assert notes["budget"]["withheld"] == ["grep"]


class TestWhenTheDeploymentAskedForAHardStop:
    """`error` is the opt-in, and it has to mean something."""

    @staticmethod
    def _run(config, messages):
        from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

        return BlockBudgetMiddleware(config=config).wrap_model_call(
            _Request(TOOLS, {"messages": messages}), lambda r: "answered"
        )

    def test_a_spent_budget_stops_the_run(self):
        from agent.src.infrastructure.block_budget import ToolBudgetExceeded

        over = [calls(*(["grep"] * 4))]
        with pytest.raises(ToolBudgetExceeded):
            self._run(ToolCallLimitConfig(per_block=3, on_exceeded="error"), over)

    def test_the_stop_names_the_tool(self):
        from agent.src.infrastructure.block_budget import ToolBudgetExceeded

        over = [calls(*(["grep"] * 4))]
        with pytest.raises(ToolBudgetExceeded, match="grep"):
            self._run(ToolCallLimitConfig(per_block=3, on_exceeded="error"), over)

    def test_the_stop_names_the_scope_and_its_ceiling(self):
        from agent.src.infrastructure.block_budget import ToolBudgetExceeded

        over = [calls(*(["grep"] * 6))]
        with pytest.raises(ToolBudgetExceeded, match="5 per conversation"):
            self._run(ToolCallLimitConfig(per_thread=5, on_exceeded="error"), over)

    def test_a_budget_still_inside_its_ceiling_runs_on(self):
        fine = [calls("grep", "grep")]
        config = ToolCallLimitConfig(per_block=3, on_exceeded="error")
        assert self._run(config, fine) == "answered"

    def test_the_default_still_carries_on_without_the_tool(self):
        over = [calls(*(["grep"] * 4))]
        assert self._run(ToolCallLimitConfig(per_block=3), over) == "answered"

    async def test_the_async_path_stops_too(self):
        from agent.src.infrastructure.block_budget import (
            BlockBudgetMiddleware,
            ToolBudgetExceeded,
        )

        async def handler(request):
            return "answered"

        with pytest.raises(ToolBudgetExceeded):
            await BlockBudgetMiddleware(
                config=ToolCallLimitConfig(per_block=3, on_exceeded="error")
            ).awrap_model_call(
                _Request(TOOLS, {"messages": [calls(*(["grep"] * 4))]}), handler
            )
