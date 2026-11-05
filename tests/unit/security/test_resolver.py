"""Authorisation order, failure semantics and trust escalation."""

from __future__ import annotations

import pytest

from agent.src.security.resolver import (
    Allowed,
    Budget,
    Effects,
    Identity,
    NeedsApproval,
    RefusalCode,
    Refused,
    RunContext,
    ToolCall,
    Trust,
    Unavailable,
    resolve,
)


class StubAuthority:
    def __init__(self, held: bool | None = True) -> None:
        self._held = held
        self.calls: list[str] = []

    def holds(self, identity: Identity, call: ToolCall) -> bool | None:
        self.calls.append(call.name)
        return self._held


class StubPolicy:
    def __init__(self, grade="allow", risk="low", reason="", unreachable=False) -> None:
        self._result = None if unreachable else (grade, risk, reason)
        self.calls: list[str] = []

    def decide(self, identity: Identity, call: ToolCall):
        self.calls.append(call.name)
        return self._result


class StubBudget:
    def __init__(self, budget: Budget | None = Budget()) -> None:
        self._budget = budget
        self.seen: list[ToolCall | None] = []

    def remaining(self, ctx: RunContext, call: ToolCall | None = None) -> Budget | None:
        self.seen.append(call)
        return self._budget


def ctx(**kwargs) -> RunContext:
    kwargs.setdefault("identity", Identity(subject="someone@example.com"))
    return RunContext(**kwargs)


def call(**kwargs) -> ToolCall:
    kwargs.setdefault("name", "tracker.create_issue")
    return ToolCall(**kwargs)


def decide(context=None, tool=None, **sources):
    sources.setdefault("authority", StubAuthority())
    sources.setdefault("policy", StubPolicy())
    sources.setdefault("budget", StubBudget())
    return resolve(context or ctx(), tool or call(), **sources)


def test_no_identity_is_unavailable_not_anonymous():
    result = decide(context=RunContext(identity=None))
    assert isinstance(result, Unavailable)
    assert result.dependency == "identity-provider"


def test_missing_authority_refuses_and_says_how_to_fix_it():
    result = decide(authority=StubAuthority(held=False), tool=call(server="tracker"))
    assert isinstance(result, Refused)
    assert result.code is RefusalCode.NO_AUTHORITY
    assert "tracker" in result.remedy


def test_unreachable_secret_source_is_unavailable_not_a_refusal():
    result = decide(authority=StubAuthority(held=None))
    assert isinstance(result, Unavailable)
    assert result.dependency == "secret-source"


def test_authority_is_checked_before_policy():
    policy = StubPolicy()
    decide(authority=StubAuthority(held=False), policy=policy)
    assert policy.calls == []


def test_unreachable_policy_fails_closed():
    result = decide(policy=StubPolicy(unreachable=True))
    assert isinstance(result, Refused)
    assert result.code is RefusalCode.POLICY_DENIED


def test_deny_refuses_with_the_policy_reason():
    result = decide(policy=StubPolicy(grade="deny", reason="tickets are read-only"))
    assert isinstance(result, Refused)
    assert result.message == "tickets are read-only"


def test_ask_carries_risk_and_reason():
    result = decide(
        policy=StubPolicy(grade="ask", risk="high", reason="writes to a shared tracker")
    )
    assert isinstance(result, NeedsApproval)
    assert result.risk == "high"
    assert result.reason == "writes to a shared tracker"


def test_allow_passes_through():
    assert isinstance(decide(), Allowed)


def test_untrusted_read_escalates_a_write_that_policy_allows():
    result = decide(
        context=ctx(trust=Trust.UNTRUSTED_READ),
        tool=call(writes=True),
        policy=StubPolicy(grade="allow"),
    )
    assert isinstance(result, NeedsApproval)
    assert "outside system" in result.reason


def test_untrusted_read_does_not_escalate_a_read():
    result = decide(context=ctx(trust=Trust.UNTRUSTED_READ), tool=call(writes=False))
    assert isinstance(result, Allowed)


def test_trust_only_moves_one_way():
    tainted = ctx().with_untrusted_read()
    assert tainted.trust is Trust.UNTRUSTED_READ
    assert tainted.with_untrusted_read() is tainted
    assert not hasattr(tainted, "clear_trust")


def test_effects_are_not_decided_twice():
    assert isinstance(
        decide(context=ctx(effects=Effects.DRY_RUN), tool=call(writes=True)), Allowed
    )


@pytest.mark.parametrize(
    "budget",
    [Budget(tokens_remaining=0), Budget(calls_remaining=0)],
)
def test_exhausted_budget_refuses_with_a_remedy(budget):
    result = decide(budget=StubBudget(budget))
    assert isinstance(result, Refused)
    assert result.code is RefusalCode.BUDGET_EXHAUSTED
    assert result.remedy


def test_unreachable_budget_fails_open():
    assert isinstance(decide(budget=StubBudget(None)), Allowed)


def test_budget_is_checked_after_policy_denies():
    result = decide(
        policy=StubPolicy(grade="deny"), budget=StubBudget(Budget(tokens_remaining=0))
    )
    assert isinstance(result, Refused)
    assert result.code is RefusalCode.POLICY_DENIED


def test_every_refusal_is_a_value_not_an_exception():
    for sources in (
        {"authority": StubAuthority(held=False)},
        {"policy": StubPolicy(grade="deny")},
        {"budget": StubBudget(Budget(tokens_remaining=0))},
    ):
        assert isinstance(decide(**sources), Refused)


def test_the_budget_is_asked_about_the_specific_call():
    budget = StubBudget()
    tool = call(name="search")
    decide(tool=tool, budget=budget)
    assert budget.seen == [tool]
