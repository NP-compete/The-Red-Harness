"""Projecting a period's spending from what has gone so far."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

PENNY = Decimal("0.01")
TOLERANCE = Decimal("1.1")


class Verdict(Enum):
    """Whether a budget period is heading for an overrun."""

    ON_TRACK = "on-track"
    WILL_OVERRUN = "will-overrun"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True)
class Period:
    """A budget period, its limit, and what has been spent."""

    starts: date
    ends: date
    limit: Decimal
    spent: Decimal

    def __post_init__(self) -> None:
        """Reject a period that ends before it starts, or negative money."""
        if self.ends < self.starts:
            raise ValueError("a period must end after it starts")
        if self.limit < 0:
            raise ValueError("a limit cannot be negative")
        if self.spent < 0:
            raise ValueError("spending cannot be negative")


@dataclass(frozen=True)
class Forecast:
    """Where spending is heading, and when the budget runs out."""

    verdict: Verdict
    per_day: Decimal
    projected_total: Decimal
    remaining: Decimal
    exhausted_on: date | None = None


def forecast(period: Period, *, today: date) -> Forecast:
    """Project `period` to its end as of `today`."""
    remaining = _money(max(Decimal("0"), period.limit - period.spent))
    elapsed = (min(today, period.ends) - period.starts).days + 1
    total_days = (period.ends - period.starts).days + 1

    if elapsed < 1:
        return Forecast(
            Verdict.ON_TRACK, _money(Decimal("0")), _money(period.spent), remaining
        )

    per_day = _money(period.spent / Decimal(elapsed))
    projected = _money(
        per_day * Decimal(total_days) if today <= period.ends else period.spent
    )

    if period.spent >= period.limit:
        return Forecast(Verdict.EXHAUSTED, per_day, projected, remaining)

    if projected > period.limit * TOLERANCE and per_day > 0:
        days_left = int(remaining / per_day)
        return Forecast(
            Verdict.WILL_OVERRUN,
            per_day,
            projected,
            remaining,
            exhausted_on=today + timedelta(days=days_left),
        )

    return Forecast(Verdict.ON_TRACK, per_day, projected, remaining)


def _money(amount: Decimal) -> Decimal:
    """`amount` rounded to the penny."""
    return amount.quantize(PENNY, rounding=ROUND_HALF_UP)
