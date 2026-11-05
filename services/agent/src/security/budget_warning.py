"""Saying how much of an allowance is left, before it runs out."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Level(str, Enum):
    """How close a budget is to being spent."""

    FINE = "fine"
    WARNING = "warning"
    SPENT = "spent"


@dataclass(frozen=True)
class Assessment:
    """Where a budget stands, and what to say about it."""

    level: Level
    remaining: int
    message: str


def assess(*, used: int, limit: int | None, warn_at: float = 0.8) -> Assessment:
    """Assess `used` against `limit`, warning at `warn_at`."""
    if limit is None:
        return Assessment(level=Level.FINE, remaining=0, message="")
    if limit <= 0:
        raise ValueError("a budget of nothing cannot be spent against")

    remaining = max(0, limit - used)
    share = used / limit

    if share >= 1:
        return Assessment(
            level=Level.SPENT,
            remaining=0,
            message="This conversation has used its allowance. Start a new one to continue.",
        )

    if share >= warn_at:
        return Assessment(
            level=Level.WARNING,
            remaining=remaining,
            message=f"{remaining} left — about {round((1 - share) * 100)}% of this allowance.",
        )

    return Assessment(level=Level.FINE, remaining=remaining, message="")
