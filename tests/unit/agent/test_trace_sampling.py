"""Deciding which traces are worth keeping."""

from __future__ import annotations

import pytest

from agent.src.agent.trace_sampling import Finished, Reason, should_keep


def finished(**kwargs) -> Finished:
    defaults = {
        "trace_id": "t-1",
        "failed": False,
        "duration_ms": 500.0,
        "approved_step": False,
        "cost": 0.01,
        "sample_rate": 0.1,
        "slow_above_ms": 5000.0,
        "costly_above": 1.0,
    }
    defaults.update(kwargs)
    return Finished(**defaults)


def test_a_failed_run_is_always_kept():
    assert should_keep(finished(failed=True)).keep is True


def test_a_failed_run_says_why_it_was_kept():
    assert should_keep(finished(failed=True)).reason is Reason.FAILED


def test_a_slow_run_is_always_kept():
    assert should_keep(finished(duration_ms=9000.0)).reason is Reason.SLOW


def test_a_run_at_the_slow_threshold_is_not_yet_slow():
    assert should_keep(finished(duration_ms=5000.0)).reason is not Reason.SLOW


def test_an_expensive_run_is_always_kept():
    assert should_keep(finished(cost=5.0)).reason is Reason.COSTLY


def test_a_run_a_person_approved_something_in_is_always_kept():
    assert should_keep(finished(approved_step=True)).reason is Reason.APPROVED


def test_failure_outranks_the_other_reasons():
    everything = finished(failed=True, duration_ms=9000.0, cost=5.0, approved_step=True)
    assert should_keep(everything).reason is Reason.FAILED


def test_an_ordinary_run_may_be_dropped():
    assert should_keep(finished(trace_id="t-drop", sample_rate=0.0)).keep is False


def test_an_ordinary_run_dropped_says_so():
    assert should_keep(finished(sample_rate=0.0)).reason is Reason.NOT_SAMPLED


def test_every_ordinary_run_is_kept_at_full_rate():
    assert should_keep(finished(sample_rate=1.0)).keep is True


def test_an_ordinary_run_kept_by_chance_says_so():
    assert should_keep(finished(sample_rate=1.0)).reason is Reason.SAMPLED


def test_the_same_trace_is_always_decided_the_same_way():
    first = should_keep(finished(trace_id="t-7", sample_rate=0.5))
    second = should_keep(finished(trace_id="t-7", sample_rate=0.5))
    assert first.keep == second.keep


def test_different_traces_do_not_all_get_the_same_answer():
    decisions = {
        should_keep(finished(trace_id=f"t-{n}", sample_rate=0.5)).keep
        for n in range(50)
    }
    assert decisions == {True, False}


def test_roughly_the_requested_share_is_kept():
    kept = sum(
        should_keep(finished(trace_id=f"t-{n}", sample_rate=0.5)).keep
        for n in range(1000)
    )
    assert 400 <= kept <= 600


def test_a_rate_outside_nothing_and_everything_is_refused():
    with pytest.raises(ValueError):
        finished(sample_rate=1.5)


def test_a_trace_without_an_identifier_is_refused():
    with pytest.raises(ValueError):
        finished(trace_id="  ")


def test_a_negative_duration_is_refused():
    with pytest.raises(ValueError):
        finished(duration_ms=-1.0)
