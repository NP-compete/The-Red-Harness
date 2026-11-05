"""What a deployment allows one person, and one team, in a day."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from agent.src.limits.fair_share import Allowance


class LimitsMisconfigured(ValueError):
    """A cap that would not apply, or could never be met."""


def _amount(section: Any, where: str, field: str = "daily_spend") -> Decimal | None:
    """`field` as a decimal amount, or `None` if it is missing or bad."""
    if not isinstance(section, dict):
        return None
    raw = section.get(field)
    if raw is None:
        return None
    try:
        found = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise LimitsMisconfigured(
            f"limits.{where}.{field} is {raw!r}, which is not an amount. "
            "A cap that cannot be read is a cap nobody is protected by."
        ) from None
    if found < 0:
        raise LimitsMisconfigured(
            f"limits.{where}.{field} is {found}, which refuses everything"
        )
    return found


def _month_covers_the_day(
    day: Decimal | None, month: Decimal | None, *, where: str
) -> None:
    """A month smaller than a day is a pair nobody can mean."""
    if day is not None and month is not None and month < day:
        raise LimitsMisconfigured(
            f"limits.{where}.monthly_spend is {month}, below its own "
            f"daily_spend of {day}, so the daily allowance could never "
            "be spent even once"
        )


def read_limits(raw: Any) -> Allowance:
    """Read the `limits` section into an allowance."""
    section = (raw or {}).get("limits") if isinstance(raw, dict) else None
    if not isinstance(section, dict):
        return Allowance(per_person=None, per_team=None)

    team_section = section.get("per_team") or {}
    team_cap = _amount(team_section, "per_team")
    team_month = _amount(team_section, "per_team", "monthly_spend")
    teams = tuple(str(name) for name in (team_section.get("teams") or []))
    _month_covers_the_day(team_cap, team_month, where="per_team")

    person_section = section.get("per_person")
    person_cap = _amount(person_section, "per_person")
    person_month = _amount(person_section, "per_person", "monthly_spend")
    _month_covers_the_day(person_cap, person_month, where="per_person")

    has_team_cap = team_cap is not None or team_month is not None

    if has_team_cap and not teams:
        raise LimitsMisconfigured(
            "limits.per_team.daily_spend is set but no teams are named, so "
            "the cap would apply to nobody. List them under per_team.teams."
        )
    if teams and not has_team_cap:
        raise LimitsMisconfigured(
            "limits.per_team.teams names teams with no daily_spend, so "
            "nothing limits them"
        )

    try:
        return Allowance(
            per_person=person_cap,
            per_team=team_cap,
            teams=teams,
            per_person_month=person_month,
            per_team_month=team_month,
        )
    except ValueError as refused:
        if isinstance(refused, LimitsMisconfigured):
            raise
        raise LimitsMisconfigured(str(refused)) from None
