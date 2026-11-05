"""Choosing what to forget when there is more remembered than there is room for."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

HALF_LIFE = timedelta(days=30)
INFERRED_WEIGHT = 0.7


@dataclass(frozen=True)
class Remembered:
    """One remembered thing, and how often it has been useful."""

    key: str
    learned_at: datetime
    last_used_at: datetime | None
    uses: int
    source: str
    pinned: bool = False


@dataclass(frozen=True)
class Pruned:
    """What was kept and what was dropped."""

    kept: tuple[Remembered, ...]
    dropped: tuple[str, ...]
    over_capacity: bool


def prune(items: list[Remembered], *, capacity: int, now: datetime) -> Pruned:
    """Keep the `capacity` most worthwhile memories as of `now`."""
    if capacity < 1:
        raise ValueError("there must be room for something")

    keys = [item.key for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError("the same thing cannot be remembered twice")

    pinned = [item for item in items if item.pinned]
    rest = sorted(
        (item for item in items if not item.pinned),
        key=lambda item: (-_worth(item, now=now), item.key),
    )

    room = max(0, capacity - len(pinned))
    kept = pinned + rest[:room]
    dropped = rest[room:]

    return Pruned(
        kept=tuple(sorted(kept, key=lambda item: item.key)),
        dropped=tuple(sorted(item.key for item in dropped)),
        over_capacity=len(kept) > capacity,
    )


def _worth(item: Remembered, *, now: datetime) -> float:
    """How much a memory is worth keeping, by use and recency."""
    if item.last_used_at is None:
        return 0.0
    age = (now - item.last_used_at) / HALF_LIFE
    recency = 1 / (1 + max(0.0, age))
    weight = 1.0 if item.source == "stated" else INFERRED_WEIGHT
    return item.uses * recency * weight
