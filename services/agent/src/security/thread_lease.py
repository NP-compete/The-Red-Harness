"""Keeps two people from running the same conversation at once."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Claim:
    """Whether a lease was granted, and who holds it if not."""

    granted: bool
    held_by: str | None = None


@dataclass(frozen=True)
class _Lease:
    """One held lease and when it lapses."""

    subject: str
    expires_at: datetime


class ThreadLeases:
    """One lease per thread, so two people cannot act on it at once."""

    def __init__(
        self,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        ttl_seconds: int = 300,
    ) -> None:
        """Start with no leases, each lasting `ttl_seconds`."""
        self._now = now
        self._ttl = timedelta(seconds=ttl_seconds)
        self._leases: dict[str, _Lease] = {}

    def holder(self, *, thread: str) -> str | None:
        """Who holds a live lease on `thread`, if anyone."""
        lease = self._live(thread)
        return lease.subject if lease else None

    def claim(self, *, thread: str, subject: str) -> Claim:
        """Claim `thread` for `subject`, renewing a lease they already hold."""
        lease = self._live(thread)
        if lease is not None and lease.subject != subject:
            return Claim(granted=False, held_by=lease.subject)

        self._leases[thread] = _Lease(
            subject=subject, expires_at=self._now() + self._ttl
        )
        return Claim(granted=True, held_by=subject)

    def release(self, *, thread: str, subject: str) -> None:
        """Release `subject`'s lease on `thread`, if they hold it."""
        lease = self._live(thread)
        if lease is not None and lease.subject == subject:
            del self._leases[thread]

    def _live(self, thread: str) -> _Lease | None:
        """The lease on `thread` if it has not lapsed, dropping it if it has."""
        lease = self._leases.get(thread)
        if lease is None:
            return None
        if self._now() >= lease.expires_at:
            del self._leases[thread]
            return None
        return lease
