"""Telling somebody what they have left, before they are refused."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from agent.src.limits.fair_share import Allowance
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

NEARLY = Decimal("0.9")

PENNY = Decimal("0.01")


def _side(spent: Decimal, cap: Decimal | None) -> dict[str, Any]:
    if cap is None:
        return {
            "spent": str(spent),
            "limit": None,
            "remaining": None,
            "nearly_out": False,
        }

    left = max(cap - spent, Decimal("0")).quantize(cap)
    return {
        "spent": str(spent),
        "limit": str(cap),
        "remaining": str(left),
        "nearly_out": cap > 0 and spent >= cap * NEARLY,
    }


def _project(
    spent: Decimal, cap: Decimal | None, *, today: Any
) -> dict[str, Any] | None:
    """Where the month is heading, against the month's budget."""
    if cap is None:
        return None

    from agent.src.security.spend_forecast import Period, forecast

    try:
        first = date(today.year, today.month, 1)
        last = date(
            today.year, today.month, calendar.monthrange(today.year, today.month)[1]
        )
        found = forecast(
            Period(starts=first, ends=last, limit=cap, spent=spent), today=today
        )
    except Exception as error:
        logger.warning("Could not project the month's spending: %s", error)
        return None

    return {
        "verdict": found.verdict.value,
        "per_day": str(found.per_day),
        "projected_total": str(found.projected_total),
        "remaining": str(found.remaining),
        "exhausted_on": found.exhausted_on.isoformat() if found.exhausted_on else None,
        "spent": str(spent.quantize(PENNY)),
        "limit": str(cap),
    }


def describe_allowance(
    *,
    allowance: Allowance,
    spent_by_person: Decimal,
    spent_by_team: Decimal,
    in_a_team: bool = True,
    month_by_person: Decimal = Decimal("0"),
    month_by_team: Decimal = Decimal("0"),
    today: Any = None,
) -> dict[str, Any]:
    """What this person has spent and may spend, and their team's."""
    when = today if today is not None else date.today()
    return {
        "person": _side(spent_by_person, allowance.per_person),
        "team": _side(spent_by_team, allowance.per_team) if in_a_team else None,
        "forecast": {
            "person": _project(month_by_person, allowance.per_person_month, today=when),
            "team": (
                _project(month_by_team, allowance.per_team_month, today=when)
                if in_a_team
                else None
            ),
        },
    }
