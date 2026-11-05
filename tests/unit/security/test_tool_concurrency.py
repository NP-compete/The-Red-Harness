"""How many calls to one tool may be in flight at once."""

from __future__ import annotations

import pytest

from agent.src.security.tool_concurrency import ConcurrencyLimits, Gate


def gate(**kwargs) -> Gate:
    defaults = {
        "limits": ConcurrencyLimits(per_tool={"deploy": 1, "search": 3}, default=2),
    }
    defaults.update(kwargs)
    return Gate(**defaults)


def test_a_first_call_is_let_through():
    assert gate().enter("search", run="r1").admitted is True


def test_calls_up_to_the_limit_are_let_through():
    g = gate()
    assert all(g.enter("search", run=f"r{n}").admitted for n in range(3))


def test_a_call_beyond_the_limit_waits():
    g = gate()
    for n in range(3):
        g.enter("search", run=f"r{n}")
    assert g.enter("search", run="r4").admitted is False


def test_a_waiting_call_says_how_many_are_ahead():
    g = gate()
    for n in range(3):
        g.enter("search", run=f"r{n}")
    assert g.enter("search", run="r4").in_flight == 3


def test_a_waiting_call_says_what_the_limit_is():
    g = gate()
    for n in range(3):
        g.enter("search", run=f"r{n}")
    assert "3" in g.enter("search", run="r4").reason


def test_leaving_frees_a_place():
    g = gate()
    for n in range(3):
        g.enter("search", run=f"r{n}")
    g.leave("search", run="r0")
    assert g.enter("search", run="r4").admitted is True


def test_leaving_something_that_never_entered_changes_nothing():
    g = gate()
    g.enter("deploy", run="r1")
    g.leave("deploy", run="never-here")
    assert g.enter("deploy", run="r2").admitted is False


def test_a_tool_without_its_own_limit_uses_the_default():
    g = gate()
    assert g.enter("other", run="r1").admitted is True
    assert g.enter("other", run="r2").admitted is True
    assert g.enter("other", run="r3").admitted is False


def test_one_tool_being_busy_does_not_block_another():
    g = gate()
    g.enter("deploy", run="r1")
    assert g.enter("search", run="r2").admitted is True


def test_the_same_run_entering_twice_takes_two_places():
    g = gate()
    g.enter("deploy", run="r1")
    assert g.enter("deploy", run="r1").admitted is False


def test_how_many_are_in_flight_can_be_read_without_entering():
    g = gate()
    g.enter("search", run="r1")
    assert g.in_flight_for("search") == 1


def test_reading_the_count_does_not_take_a_place():
    g = gate()
    g.in_flight_for("deploy")
    assert g.enter("deploy", run="r1").admitted is True


def test_a_refused_call_does_not_take_a_place():
    g = gate()
    g.enter("deploy", run="r1")
    g.enter("deploy", run="r2")
    g.leave("deploy", run="r1")
    assert g.enter("deploy", run="r3").admitted is True


def test_a_tool_limited_to_nothing_is_refused():
    with pytest.raises(ValueError):
        ConcurrencyLimits(per_tool={"deploy": 0}, default=1)


def test_a_default_of_nothing_is_refused():
    with pytest.raises(ValueError):
        ConcurrencyLimits(per_tool={}, default=0)


def test_entering_without_a_tool_is_refused():
    with pytest.raises(ValueError):
        gate().enter("  ", run="r1")
