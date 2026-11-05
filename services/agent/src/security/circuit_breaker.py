"""Backing off from a system that keeps failing, per system."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class State(str, Enum):
    """Whether a breaker is letting calls through."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _Record:
    """A breaker's failure count and when it last opened."""

    failures: int = 0
    opened_at: datetime | None = None


class Breakers:
    """One circuit breaker per named dependency."""

    def __init__(
        self,
        *,
        threshold: int = 3,
        cooldown_seconds: int = 60,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        """Open after `threshold` failures, retry after `cooldown_seconds`."""
        if threshold <= 0:
            raise ValueError("a breaker that opens on no failures breaks everything")
        self._threshold = threshold
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._now = now
        self._records: dict[str, _Record] = {}

    def state(self, name: str) -> State:
        """Whether the breaker for `name` is closed, open, or half open."""
        record = self._records.get(name)
        if record is None or record.opened_at is None:
            return State.CLOSED
        if self._now() - record.opened_at >= self._cooldown:
            return State.HALF_OPEN
        return State.OPEN

    def failed(self, name: str) -> None:
        """Count a failure against `name`, opening the breaker at the threshold."""
        record = self._records.setdefault(name, _Record())
        record.failures += 1
        if record.failures >= self._threshold or record.opened_at is not None:
            record.opened_at = self._now()

    def succeeded(self, name: str) -> None:
        """Clear the failures recorded against `name`."""
        self._records.pop(name, None)

    def unavailable(self) -> tuple[str, ...]:
        """Every dependency whose breaker is not closed, sorted."""
        return tuple(
            sorted(
                name for name in self._records if self.state(name) is not State.CLOSED
            )
        )
