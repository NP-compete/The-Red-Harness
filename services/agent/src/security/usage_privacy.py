"""Usage figures that do not quietly become a report on individuals."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    """One run's usage, and who it was for."""

    subject: str
    team: str
    tokens: int
    approvals: int
    refusals: int


@dataclass(frozen=True)
class Usage:
    """Usage totals, by team and optionally by person."""

    totals: dict[str, int] = field(default_factory=dict)
    per_team: dict[str, dict[str, int]] = field(default_factory=dict)
    per_person: dict[str, dict[str, int]] = field(default_factory=dict)
    discloses_individuals: bool = False


_FIELDS = ("tokens", "approvals", "refusals")


def summarise(
    events: list[Event], *, per_person: bool, min_team_size: int = 2
) -> Usage:
    """Summarise `events`, withholding teams too small to stay anonymous."""
    if min_team_size <= 0:
        raise ValueError("a team floor of nothing exposes a team of one")

    totals = {name: sum(getattr(e, name) for e in events) for name in _FIELDS}

    by_team: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(_FIELDS, 0))
    members: dict[str, set[str]] = defaultdict(set)
    by_person: dict[str, dict[str, int]] = defaultdict(
        lambda: dict.fromkeys(_FIELDS, 0)
    )

    for event in events:
        members[event.team].add(event.subject)
        for name in _FIELDS:
            by_team[event.team][name] += getattr(event, name)
            by_person[event.subject][name] += getattr(event, name)

    teams = {
        team: figures
        for team, figures in by_team.items()
        if len(members[team]) >= min_team_size
    }

    return Usage(
        totals=totals,
        per_team=teams,
        per_person=dict(by_person) if per_person else {},
        discloses_individuals=per_person,
    )
