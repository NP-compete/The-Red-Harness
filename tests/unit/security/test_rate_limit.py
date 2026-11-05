"""Holding a caller to an agreed rate without punishing a normal burst."""

from __future__ import annotations

import pytest

from agent.src.security.rate_limit import Limit, RateLimiter


def limiter(**kwargs) -> RateLimiter:
    defaults = {"limit": Limit(per_second=2.0, burst=4)}
    defaults.update(kwargs)
    return RateLimiter(**defaults)


def test_a_first_call_is_allowed():
    assert limiter().check("ana", now=0.0).allowed is True


def test_a_short_burst_is_allowed():
    rate = limiter()
    assert all(rate.check("ana", now=0.0).allowed for _ in range(4))


def test_a_burst_beyond_the_allowance_is_refused():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=0.0)
    assert rate.check("ana", now=0.0).allowed is False


def test_a_refusal_says_how_long_to_wait():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=0.0)
    assert rate.check("ana", now=0.0).retry_after == pytest.approx(0.5)


def test_waiting_the_stated_time_is_enough():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=0.0)
    assert rate.check("ana", now=0.5).allowed is True


def test_the_allowance_refills_over_time():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=0.0)
    assert rate.check("ana", now=2.0).allowed is True


def test_the_allowance_does_not_refill_past_the_burst():
    rate = limiter()
    rate.check("ana", now=0.0)
    for _ in range(4):
        assert rate.check("ana", now=100.0).allowed is True
    assert rate.check("ana", now=100.0).allowed is False


def test_one_caller_does_not_spend_anothers_allowance():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=0.0)
    assert rate.check("bo", now=0.0).allowed is True


def test_a_refusal_says_what_the_limit_was():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=0.0)
    assert "2" in rate.check("ana", now=0.0).reason


def test_an_allowed_call_has_nothing_to_wait_for():
    assert limiter().check("ana", now=0.0).retry_after == 0.0


def test_the_remaining_allowance_is_reported():
    rate = limiter()
    rate.check("ana", now=0.0)
    assert rate.check("ana", now=0.0).remaining == 2


def test_time_running_backwards_does_not_grant_free_calls():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=10.0)
    assert rate.check("ana", now=0.0).allowed is False


def test_a_check_that_is_refused_does_not_consume_the_allowance():
    rate = limiter()
    for _ in range(4):
        rate.check("ana", now=0.0)
    rate.check("ana", now=0.0)
    assert rate.check("ana", now=0.5).allowed is True


def test_peeking_does_not_spend_the_allowance():
    rate = limiter()
    rate.peek("ana", now=0.0)
    assert rate.check("ana", now=0.0).remaining == 3


def test_a_zero_rate_is_refused():
    with pytest.raises(ValueError):
        Limit(per_second=0.0, burst=1)


def test_a_zero_burst_is_refused():
    with pytest.raises(ValueError):
        Limit(per_second=1.0, burst=0)


def test_an_empty_key_is_refused():
    with pytest.raises(ValueError):
        limiter().check("  ", now=0.0)
