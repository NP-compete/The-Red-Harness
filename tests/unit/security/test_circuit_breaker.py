"""Backing off from a system that keeps failing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.circuit_breaker import Breakers, State

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def breakers(**kwargs) -> Breakers:
    clock = {"now": kwargs.pop("now", NOW)}
    b = Breakers(now=lambda: clock["now"], **kwargs)
    b.advance = lambda seconds: clock.__setitem__(
        "now", clock["now"] + timedelta(seconds=seconds)
    )
    return b


def test_a_quiet_system_is_available():
    assert breakers().state("tracker") is State.CLOSED


def test_one_failure_does_not_break_anything():
    b = breakers(threshold=3)
    b.failed("tracker")
    assert b.state("tracker") is State.CLOSED


def test_enough_failures_opens_the_breaker():
    b = breakers(threshold=2)
    b.failed("tracker")
    b.failed("tracker")
    assert b.state("tracker") is State.OPEN


def test_a_success_clears_the_count():
    b = breakers(threshold=2)
    b.failed("tracker")
    b.succeeded("tracker")
    b.failed("tracker")
    assert b.state("tracker") is State.CLOSED


def test_one_system_breaking_does_not_affect_another():
    b = breakers(threshold=1)
    b.failed("tracker")
    assert b.state("docs") is State.CLOSED


def test_an_open_breaker_lets_one_request_through_after_a_pause():
    b = breakers(threshold=1, cooldown_seconds=30)
    b.failed("tracker")
    b.advance(31)
    assert b.state("tracker") is State.HALF_OPEN


def test_a_success_while_testing_closes_the_breaker():
    b = breakers(threshold=1, cooldown_seconds=30)
    b.failed("tracker")
    b.advance(31)
    b.succeeded("tracker")
    assert b.state("tracker") is State.CLOSED


def test_a_failure_while_testing_opens_it_again():
    b = breakers(threshold=1, cooldown_seconds=30)
    b.failed("tracker")
    b.advance(31)
    b.failed("tracker")
    assert b.state("tracker") is State.OPEN


def test_the_breaker_stays_open_during_the_pause():
    b = breakers(threshold=1, cooldown_seconds=30)
    b.failed("tracker")
    b.advance(29)
    assert b.state("tracker") is State.OPEN


def test_what_broke_is_reportable():
    b = breakers(threshold=1)
    b.failed("tracker")
    assert b.unavailable() == ("tracker",)


def test_nothing_broken_reports_nothing():
    assert breakers().unavailable() == ()


@pytest.mark.parametrize("threshold", [0, -1])
def test_a_nonsense_threshold_is_refused(threshold):
    with pytest.raises(ValueError):
        Breakers(threshold=threshold)
