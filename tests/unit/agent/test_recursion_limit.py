"""How deep agents may call other agents, and when that is a cycle."""

from __future__ import annotations

import pytest

from agent.src.agent.recursion_limit import Refusal, Spawn, may_spawn


def spawn(**kwargs) -> Spawn:
    defaults = {
        "parent": "triage",
        "child": "researcher",
        "ancestry": ("triage",),
        "max_depth": 3,
        "siblings_running": 0,
        "max_siblings": 4,
    }
    defaults.update(kwargs)
    return Spawn(**defaults)


def test_a_first_subagent_is_allowed():
    assert may_spawn(spawn()).permitted is True


def test_the_depth_it_would_reach_is_reported():
    assert may_spawn(spawn()).depth == 2


def test_nesting_within_the_limit_is_allowed():
    deep = spawn(ancestry=("triage", "researcher"), parent="researcher", child="reader")
    assert may_spawn(deep).permitted is True


def test_nesting_past_the_limit_is_refused():
    too_deep = spawn(
        ancestry=("triage", "researcher", "reader"), parent="reader", child="skimmer"
    )
    assert may_spawn(too_deep).refusal is Refusal.TOO_DEEP


def test_a_refusal_for_depth_says_what_the_limit_is():
    too_deep = spawn(
        ancestry=("triage", "researcher", "reader"), parent="reader", child="skimmer"
    )
    assert "3" in may_spawn(too_deep).reason


def test_an_agent_cannot_call_itself():
    assert may_spawn(spawn(child="triage")).refusal is Refusal.CYCLE


def test_an_agent_cannot_call_something_already_above_it():
    loop = spawn(ancestry=("triage", "researcher"), parent="researcher", child="triage")
    assert may_spawn(loop).refusal is Refusal.CYCLE


def test_a_cycle_names_the_agent_that_would_repeat():
    loop = spawn(ancestry=("triage", "researcher"), parent="researcher", child="triage")
    assert "triage" in may_spawn(loop).reason


def test_a_cycle_is_refused_even_within_the_depth_limit():
    loop = spawn(ancestry=("triage",), child="triage", max_depth=10)
    assert may_spawn(loop).permitted is False


def test_too_many_at_once_is_refused():
    crowded = spawn(siblings_running=4, max_siblings=4)
    assert may_spawn(crowded).refusal is Refusal.TOO_MANY


def test_a_refusal_for_width_says_how_many_are_running():
    crowded = spawn(siblings_running=4, max_siblings=4)
    assert "4" in may_spawn(crowded).reason


def test_depth_is_checked_before_width():
    both = spawn(
        ancestry=("triage", "researcher", "reader"),
        parent="reader",
        child="skimmer",
        siblings_running=9,
        max_siblings=4,
    )
    assert may_spawn(both).refusal is Refusal.TOO_DEEP


def test_a_cycle_outranks_everything_else():
    everything = spawn(
        ancestry=("triage", "researcher", "reader"),
        parent="reader",
        child="triage",
        siblings_running=9,
    )
    assert may_spawn(everything).refusal is Refusal.CYCLE


def test_how_much_room_is_left_below_is_reported():
    assert may_spawn(spawn()).depth_remaining == 1


def test_nothing_is_left_below_at_the_limit():
    deep = spawn(ancestry=("triage", "researcher"), parent="researcher", child="reader")
    assert may_spawn(deep).depth_remaining == 0


def test_a_spawn_whose_parent_is_not_in_its_ancestry_is_refused():
    with pytest.raises(ValueError):
        Spawn(
            parent="stranger",
            child="researcher",
            ancestry=("triage",),
            max_depth=3,
            siblings_running=0,
            max_siblings=4,
        )


def test_a_depth_limit_of_nothing_is_refused():
    with pytest.raises(ValueError):
        spawn(max_depth=0)
