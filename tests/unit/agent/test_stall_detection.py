"""Noticing when a run has stopped producing anything."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.agent.stall_detection import Activity, State, check_stall

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def activity(**kwargs) -> Activity:
    defaults = {
        "last_output_at": NOW - timedelta(seconds=5),
        "last_tool_started_at": None,
        "waiting_on_person": False,
        "tool_running": "",
        "patience": timedelta(seconds=60),
    }
    defaults.update(kwargs)
    return Activity(**defaults)


def test_a_run_producing_output_is_working():
    assert check_stall(activity(), now=NOW).state is State.WORKING


def test_a_run_silent_for_a_while_has_stalled():
    quiet = activity(last_output_at=NOW - timedelta(minutes=5))
    assert check_stall(quiet, now=NOW).state is State.STALLED


def test_a_run_inside_a_long_tool_call_is_not_stalled():
    busy = activity(
        last_output_at=NOW - timedelta(minutes=5),
        last_tool_started_at=NOW - timedelta(seconds=10),
        tool_running="search",
    )
    assert check_stall(busy, now=NOW).state is State.WORKING


def test_a_tool_call_that_has_run_too_long_is_itself_a_stall():
    stuck = activity(
        last_output_at=NOW - timedelta(minutes=5),
        last_tool_started_at=NOW - timedelta(minutes=5),
        tool_running="search",
    )
    assert check_stall(stuck, now=NOW).state is State.TOOL_HUNG


def test_a_hung_tool_is_named():
    stuck = activity(
        last_output_at=NOW - timedelta(minutes=5),
        last_tool_started_at=NOW - timedelta(minutes=5),
        tool_running="search",
    )
    assert "search" in check_stall(stuck, now=NOW).reason


def test_a_run_waiting_for_a_person_is_not_stalled():
    waiting = activity(last_output_at=NOW - timedelta(hours=2), waiting_on_person=True)
    assert check_stall(waiting, now=NOW).state is State.WAITING


def test_waiting_for_a_person_outranks_a_hung_tool():
    both = activity(
        last_output_at=NOW - timedelta(hours=2),
        last_tool_started_at=NOW - timedelta(hours=2),
        tool_running="deploy",
        waiting_on_person=True,
    )
    assert check_stall(both, now=NOW).state is State.WAITING


def test_how_long_it_has_been_quiet_is_reported():
    quiet = activity(last_output_at=NOW - timedelta(minutes=5))
    assert check_stall(quiet, now=NOW).quiet_for == timedelta(minutes=5)


def test_a_stalled_run_should_be_looked_at():
    quiet = activity(last_output_at=NOW - timedelta(minutes=5))
    assert check_stall(quiet, now=NOW).needs_attention is True


def test_a_working_run_needs_no_attention():
    assert check_stall(activity(), now=NOW).needs_attention is False


def test_a_waiting_run_needs_no_attention():
    waiting = activity(last_output_at=NOW - timedelta(hours=2), waiting_on_person=True)
    assert check_stall(waiting, now=NOW).needs_attention is False


def test_patience_can_be_set_per_run():
    quiet = activity(
        last_output_at=NOW - timedelta(seconds=30), patience=timedelta(seconds=10)
    )
    assert check_stall(quiet, now=NOW).state is State.STALLED


def test_a_generous_patience_tolerates_a_longer_silence():
    quiet = activity(
        last_output_at=NOW - timedelta(minutes=5), patience=timedelta(minutes=10)
    )
    assert check_stall(quiet, now=NOW).state is State.WORKING


def test_a_run_that_has_never_produced_anything_is_measured_from_its_start():
    fresh = activity(last_output_at=NOW - timedelta(seconds=1))
    assert check_stall(fresh, now=NOW).state is State.WORKING


def test_output_dated_in_the_future_is_not_trusted():
    odd = activity(last_output_at=NOW + timedelta(minutes=1))
    assert check_stall(odd, now=NOW).quiet_for == timedelta(0)


def test_a_tool_running_without_a_start_time_is_refused():
    with pytest.raises(ValueError):
        activity(tool_running="search", last_tool_started_at=None)


def test_a_patience_of_nothing_is_refused():
    with pytest.raises(ValueError):
        activity(patience=timedelta(0))
