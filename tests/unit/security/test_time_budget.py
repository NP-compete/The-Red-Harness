"""Deciding whether there is time left to take another step."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.time_budget import Outcome, TimeBudget, may_continue

START = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def budget(**kwargs) -> TimeBudget:
    defaults = {
        "started_at": START,
        "limit": timedelta(minutes=10),
        "reserve": timedelta(seconds=30),
    }
    defaults.update(kwargs)
    return TimeBudget(**defaults)


def test_a_fresh_run_may_continue():
    assert (
        may_continue(budget(), expected_step=timedelta(seconds=5), now=START).outcome
        is Outcome.CONTINUE
    )


def test_a_run_with_time_left_reports_how_much():
    decision = may_continue(budget(), expected_step=timedelta(seconds=5), now=START)
    assert decision.remaining == timedelta(minutes=10)


def test_a_run_past_its_limit_stops():
    late = START + timedelta(minutes=11)
    assert (
        may_continue(budget(), expected_step=timedelta(seconds=5), now=late).outcome
        is Outcome.OUT_OF_TIME
    )


def test_a_run_past_its_limit_says_so():
    late = START + timedelta(minutes=11)
    assert (
        "time"
        in may_continue(budget(), expected_step=timedelta(seconds=5), now=late).reason
    )


def test_a_step_that_would_not_finish_in_time_is_not_started():
    nearly = START + timedelta(minutes=9, seconds=50)
    decision = may_continue(budget(), expected_step=timedelta(seconds=30), now=nearly)
    assert decision.outcome is Outcome.STEP_TOO_LONG


def test_a_step_that_would_not_finish_says_what_it_needed():
    nearly = START + timedelta(minutes=9, seconds=50)
    decision = may_continue(budget(), expected_step=timedelta(seconds=30), now=nearly)
    assert "30" in decision.reason


def test_the_reserve_is_kept_back_for_finishing_up():
    nearly = START + timedelta(minutes=9, seconds=40)
    decision = may_continue(budget(), expected_step=timedelta(seconds=15), now=nearly)
    assert decision.outcome is Outcome.STEP_TOO_LONG


def test_a_step_that_fits_inside_the_reserve_boundary_runs():
    comfortable = START + timedelta(minutes=9)
    decision = may_continue(
        budget(), expected_step=timedelta(seconds=15), now=comfortable
    )
    assert decision.outcome is Outcome.CONTINUE


def test_an_unknown_step_length_is_assumed_to_be_long():
    nearly = START + timedelta(minutes=9, seconds=45)
    assert (
        may_continue(budget(), expected_step=None, now=nearly).outcome
        is Outcome.STEP_TOO_LONG
    )


def test_an_unknown_step_length_early_on_is_fine():
    assert (
        may_continue(budget(), expected_step=None, now=START).outcome
        is Outcome.CONTINUE
    )


def test_a_run_without_a_limit_always_continues():
    endless = budget(limit=None)
    late = START + timedelta(days=1)
    assert (
        may_continue(endless, expected_step=timedelta(hours=1), now=late).outcome
        is Outcome.CONTINUE
    )


def test_a_run_without_a_limit_has_no_remaining_time_to_report():
    endless = budget(limit=None)
    assert may_continue(endless, expected_step=None, now=START).remaining is None


def test_a_run_is_warned_when_time_is_nearly_gone():
    nearly = START + timedelta(minutes=9, seconds=10)
    assert (
        may_continue(budget(), expected_step=timedelta(seconds=5), now=nearly).warn
        is True
    )


def test_a_run_with_plenty_of_time_is_not_warned():
    assert (
        may_continue(budget(), expected_step=timedelta(seconds=5), now=START).warn
        is False
    )


def test_running_out_of_time_is_not_treated_as_a_failure():
    late = START + timedelta(minutes=11)
    assert may_continue(budget(), expected_step=None, now=late).failed is False


def test_a_reserve_larger_than_the_limit_is_refused():
    with pytest.raises(ValueError):
        TimeBudget(
            started_at=START, limit=timedelta(seconds=10), reserve=timedelta(minutes=1)
        )


@pytest.mark.parametrize("limit", [timedelta(0), timedelta(seconds=-1)])
def test_a_limit_of_no_time_is_refused(limit):
    with pytest.raises(ValueError):
        TimeBudget(started_at=START, limit=limit, reserve=timedelta(0))
