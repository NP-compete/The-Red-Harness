"""Whether indexed material still matches where it came from."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

ABANDON_AFTER = timedelta(days=30)


class State(Enum):
    """How current a source's index is."""

    CURRENT = "current"
    BEHIND = "behind"
    STALE = "stale"
    UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class Source:
    """One indexed source, when it was indexed and when it next should be."""

    name: str
    indexed_at: datetime | None
    origin_changed_at: datetime | None
    refresh_every: timedelta | None
    unreachable_since: datetime | None

    def __post_init__(self) -> None:
        """Reject a nameless or never-indexed source, or a zero interval."""
        if not self.name.strip():
            raise ValueError("a source must have a name")
        if self.indexed_at is None:
            raise ValueError("a source that was never indexed has nothing to assess")
        if self.refresh_every is not None and self.refresh_every <= timedelta(0):
            raise ValueError("a refresh interval must be some time")


@dataclass(frozen=True)
class Freshness:
    """How current a source is, and the caveat to cite it with."""

    state: State
    citable: bool
    caveat: str = ""
    due_at: datetime | None = None


def assess_freshness(source: Source, *, now: datetime) -> Freshness:
    """Assess how current `source` is as of `now`."""
    indexed_at = source.indexed_at
    assert indexed_at is not None
    due_at = indexed_at + source.refresh_every if source.refresh_every else None

    if source.unreachable_since is not None:
        days = (now - source.unreachable_since).days
        return Freshness(
            State.UNREACHABLE,
            citable=now - source.unreachable_since <= ABANDON_AFTER,
            caveat=f"this source has been unreachable for {days} days",
            due_at=due_at,
        )

    if source.origin_changed_at is not None and source.origin_changed_at > indexed_at:
        return Freshness(
            State.BEHIND,
            citable=True,
            caveat="the original has changed since this was indexed",
            due_at=due_at,
        )

    if due_at is not None and now > due_at:
        return Freshness(
            State.STALE,
            citable=True,
            caveat=f"this was last indexed {(now - indexed_at).days} days ago",
            due_at=due_at,
        )

    return Freshness(State.CURRENT, citable=True, due_at=due_at)
