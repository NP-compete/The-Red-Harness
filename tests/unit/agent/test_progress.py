"""Saying how far along a long piece of work is."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.agent.progress import Plan, Step, report_progress

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def plan(**kwargs) -> Plan:
    defaults = {
        "steps": (
            Step(name="read the brief", done=True, seconds=10.0),
            Step(name="gather figures", done=True, seconds=50.0),
            Step(name="write the summary", done=False, seconds=None),
        ),
        "started_at": NOW - timedelta(minutes=1),
        "open_ended": False,
    }
    defaults.update(kwargs)
    return Plan(**defaults)


def test_what_is_happening_now_is_named():
    assert report_progress(plan(), now=NOW).doing == "write the summary"


def test_a_finished_plan_is_doing_nothing():
    done = plan(steps=(Step(name="a", done=True, seconds=1.0),))
    assert report_progress(done, now=NOW).doing == ""


def test_how_many_steps_are_done_is_reported():
    assert report_progress(plan(), now=NOW).done == 2


def test_how_many_steps_there_are_is_reported():
    assert report_progress(plan(), now=NOW).total == 3


def test_the_share_completed_is_reported():
    assert report_progress(plan(), now=NOW).fraction == pytest.approx(2 / 3)


def test_a_finished_plan_is_fully_complete():
    done = plan(steps=(Step(name="a", done=True, seconds=1.0),))
    assert report_progress(done, now=NOW).fraction == 1.0


def test_time_remaining_is_estimated_from_what_steps_have_taken():
    assert report_progress(plan(), now=NOW).remaining == timedelta(seconds=30)


def test_no_estimate_is_given_before_anything_has_finished():
    fresh = plan(
        steps=(
            Step(name="a", done=False, seconds=None),
            Step(name="b", done=False, seconds=None),
        )
    )
    assert report_progress(fresh, now=NOW).remaining is None


def test_an_open_ended_plan_gives_no_estimate_however_much_is_done():
    assert report_progress(plan(open_ended=True), now=NOW).remaining is None


def test_an_open_ended_plan_says_the_count_may_grow():
    assert report_progress(plan(open_ended=True), now=NOW).total_is_final is False


def test_a_fixed_plan_says_the_count_is_final():
    assert report_progress(plan(), now=NOW).total_is_final is True


def test_an_open_ended_plan_still_reports_what_is_done():
    assert report_progress(plan(open_ended=True), now=NOW).done == 2


def test_an_open_ended_plan_shows_no_share_rather_than_a_misleading_one():
    assert report_progress(plan(open_ended=True), now=NOW).fraction is None


def test_a_plan_running_far_longer_than_expected_says_so():
    slow = plan(started_at=NOW - timedelta(hours=2))
    assert report_progress(slow, now=NOW).overrunning is True


def test_a_plan_running_to_time_is_not_overrunning():
    assert report_progress(plan(), now=NOW).overrunning is False


def test_how_long_it_has_been_running_is_reported():
    assert report_progress(plan(), now=NOW).elapsed == timedelta(minutes=1)


def test_a_plan_with_no_steps_is_refused():
    with pytest.raises(ValueError):
        Plan(steps=(), started_at=NOW, open_ended=False)


def test_a_step_that_is_done_without_a_duration_is_refused():
    with pytest.raises(ValueError):
        Step(name="a", done=True, seconds=None)


def test_a_step_without_a_name_is_refused():
    with pytest.raises(ValueError):
        Step(name="  ", done=False, seconds=None)
