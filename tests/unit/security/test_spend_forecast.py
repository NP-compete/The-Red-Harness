"""Working out whether the money will last the month."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from agent.src.security.spend_forecast import Period, Verdict, forecast


def period(**kwargs) -> Period:
    defaults = {
        "starts": date(2026, 10, 1),
        "ends": date(2026, 10, 31),
        "limit": Decimal("3000.00"),
        "spent": Decimal("1000.00"),
    }
    defaults.update(kwargs)
    return Period(**defaults)


def test_spending_on_track_is_on_track():
    assert forecast(period(), today=date(2026, 10, 10)).verdict is Verdict.ON_TRACK


def test_spending_slowly_is_still_on_track():
    assert (
        forecast(period(spent=Decimal("200")), today=date(2026, 10, 10)).verdict
        is Verdict.ON_TRACK
    )


def test_spending_fast_is_projected_to_overrun():
    fast = period(spent=Decimal("2000"))
    assert forecast(fast, today=date(2026, 10, 10)).verdict is Verdict.WILL_OVERRUN


def test_an_overrun_says_when_the_money_runs_out():
    fast = period(spent=Decimal("2000"))
    assert forecast(fast, today=date(2026, 10, 10)).exhausted_on == date(2026, 10, 15)


def test_money_already_gone_is_reported_as_gone():
    spent = period(spent=Decimal("3000"))
    assert forecast(spent, today=date(2026, 10, 10)).verdict is Verdict.EXHAUSTED


def test_overspending_is_reported_as_gone_rather_than_as_a_projection():
    over = period(spent=Decimal("3200"))
    assert forecast(over, today=date(2026, 10, 10)).verdict is Verdict.EXHAUSTED


def test_the_daily_rate_is_reported():
    assert forecast(period(), today=date(2026, 10, 10)).per_day == Decimal("100.00")


def test_the_projected_total_is_reported():
    projected = forecast(period(), today=date(2026, 10, 10)).projected_total
    assert projected == Decimal("3100.00")


def test_what_is_left_is_reported():
    assert forecast(period(), today=date(2026, 10, 10)).remaining == Decimal("2000.00")


def test_nothing_is_left_when_it_is_overspent():
    assert forecast(
        period(spent=Decimal("3200")), today=date(2026, 10, 10)
    ).remaining == Decimal("0")


def test_the_first_day_does_not_divide_by_zero():
    first = forecast(period(spent=Decimal("50")), today=date(2026, 10, 1))
    assert first.per_day == Decimal("50.00")


def test_a_day_before_the_period_has_spent_nothing():
    early = forecast(period(spent=Decimal("0")), today=date(2026, 9, 28))
    assert early.verdict is Verdict.ON_TRACK


def test_a_day_after_the_period_is_not_projected_forward():
    late = forecast(period(spent=Decimal("1000")), today=date(2026, 11, 5))
    assert late.projected_total == Decimal("1000.00")


def test_money_is_never_reported_in_fractions_of_a_penny():
    odd = period(limit=Decimal("1000"), spent=Decimal("333.333333"))
    assert forecast(odd, today=date(2026, 10, 10)).per_day.as_tuple().exponent == -2


def test_a_period_that_ends_before_it_starts_is_refused():
    with pytest.raises(ValueError):
        Period(
            starts=date(2026, 10, 31),
            ends=date(2026, 10, 1),
            limit=Decimal("1"),
            spent=Decimal("0"),
        )


def test_a_negative_limit_is_refused():
    with pytest.raises(ValueError):
        Period(
            starts=date(2026, 10, 1),
            ends=date(2026, 10, 31),
            limit=Decimal("-1"),
            spent=Decimal("0"),
        )


def test_negative_spending_is_refused():
    with pytest.raises(ValueError):
        Period(
            starts=date(2026, 10, 1),
            ends=date(2026, 10, 31),
            limit=Decimal("10"),
            spent=Decimal("-1"),
        )
