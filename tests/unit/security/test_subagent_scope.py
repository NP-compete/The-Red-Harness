"""What a subagent is allowed to do on behalf of the agent that called it."""

from __future__ import annotations

import pytest

from agent.src.security.subagent_scope import Subagent, scope_for


def parent_tools() -> list[str]:
    return ["tracker.search", "tracker.create_issue", "docs.search", "mail.send"]


def sub(**kwargs) -> Subagent:
    defaults = {
        "name": "researcher",
        "tools": ["tracker.search", "docs.search"],
        "writes": False,
    }
    defaults.update(kwargs)
    return Subagent(**defaults)


def test_a_subagent_gets_the_tools_it_declares():
    assert scope_for(sub(), parent_tools=parent_tools()).tools == (
        "docs.search",
        "tracker.search",
    )


def test_a_subagent_cannot_reach_a_tool_the_parent_does_not_have():
    scoped = scope_for(sub(tools=["secret.tool"]), parent_tools=parent_tools())
    assert scoped.tools == ()


def test_a_read_only_subagent_loses_acting_tools():
    scoped = scope_for(
        sub(tools=["tracker.create_issue", "docs.search"], writes=False),
        parent_tools=parent_tools(),
        acting_tools=["tracker.create_issue"],
    )
    assert scoped.tools == ("docs.search",)


def test_a_subagent_allowed_to_act_keeps_them():
    scoped = scope_for(
        sub(tools=["tracker.create_issue"], writes=True),
        parent_tools=parent_tools(),
        acting_tools=["tracker.create_issue"],
    )
    assert scoped.tools == ("tracker.create_issue",)


def test_a_subagent_declaring_nothing_gets_nothing():
    assert scope_for(sub(tools=[]), parent_tools=parent_tools()).tools == ()


def test_what_was_refused_is_reported():
    scoped = scope_for(
        sub(tools=["secret.tool", "docs.search"]), parent_tools=parent_tools()
    )
    assert scoped.refused == ("secret.tool",)


def test_the_parent_trust_state_carries_into_the_subagent():
    scoped = scope_for(sub(), parent_tools=parent_tools(), parent_tainted=True)
    assert scoped.tainted is True


def test_a_clean_parent_leaves_the_subagent_clean():
    assert scope_for(sub(), parent_tools=parent_tools()).tainted is False


def test_a_subagent_cannot_widen_its_own_budget():
    scoped = scope_for(sub(), parent_tools=parent_tools(), parent_calls_remaining=3)
    assert scoped.calls_remaining == 3


def test_a_subagent_budget_is_capped_by_what_it_asks_for():
    scoped = scope_for(
        sub(), parent_tools=parent_tools(), parent_calls_remaining=10, requested_calls=4
    )
    assert scoped.calls_remaining == 4


def test_asking_for_more_than_the_parent_has_does_not_grant_it():
    scoped = scope_for(
        sub(), parent_tools=parent_tools(), parent_calls_remaining=2, requested_calls=10
    )
    assert scoped.calls_remaining == 2


def test_a_subagent_must_be_named():
    with pytest.raises(ValueError):
        Subagent(name="  ", tools=[], writes=False)
