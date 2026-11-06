"""What a run has left to spend, counted against the configured limits."""

from __future__ import annotations

from agent.src.agent.config.middleware import ToolCallLimitConfig
from agent.src.security.budget import RunBudget
from agent.src.security.resolver import Identity, RunContext, ToolCall

CTX = RunContext(identity=Identity(subject="someone@example.com"))


def budget(*, run_limit=3, per_tool=None, enabled=True, tokens=None) -> RunBudget:
    return RunBudget(
        ToolCallLimitConfig(
            enabled=enabled, run_limit=run_limit, per_tool=per_tool or {}
        ),
        token_limit=tokens,
    )


def test_a_fresh_run_has_its_full_allowance():
    assert budget(run_limit=3).remaining(CTX).calls_remaining == 3


def test_each_call_spends_one():
    b = budget(run_limit=3)
    b.record(ToolCall(name="search"))
    assert b.remaining(CTX).calls_remaining == 2


def test_the_allowance_stops_at_zero_rather_than_going_negative():
    b = budget(run_limit=1)
    b.record(ToolCall(name="search"))
    b.record(ToolCall(name="search"))
    assert b.remaining(CTX).calls_remaining == 0


def test_a_per_tool_ceiling_runs_out_before_the_run_does():
    b = budget(run_limit=100, per_tool={"search": 1})
    b.record(ToolCall(name="search"))
    assert b.remaining(CTX, ToolCall(name="search")).calls_remaining == 0
    assert b.remaining(CTX, ToolCall(name="other")).calls_remaining > 0


def test_a_tool_without_a_ceiling_uses_the_run_allowance():
    b = budget(run_limit=5, per_tool={"search": 1})
    assert b.remaining(CTX, ToolCall(name="other")).calls_remaining == 5


def test_disabled_limits_mean_no_ceiling():
    b = budget(enabled=False, run_limit=1)
    b.record(ToolCall(name="search"))
    b.record(ToolCall(name="search"))
    assert b.remaining(CTX).calls_remaining is None


def test_tokens_are_counted_when_a_limit_is_set():
    b = budget(tokens=1000)
    b.record_tokens(400)
    assert b.remaining(CTX).tokens_remaining == 600


def test_tokens_are_unlimited_when_no_limit_is_set():
    b = budget()
    b.record_tokens(400)
    assert b.remaining(CTX).tokens_remaining is None


def test_token_allowance_stops_at_zero():
    b = budget(tokens=100)
    b.record_tokens(250)
    assert b.remaining(CTX).tokens_remaining == 0


def test_spend_is_reported_for_attribution():
    b = budget()
    b.record(ToolCall(name="search"))
    b.record_tokens(120)
    assert b.spent == (1, 120)
