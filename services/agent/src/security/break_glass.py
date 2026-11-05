"""Emergency access, granted by somebody else and expiring on its own."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class Entry:
    """One emergency-access request and what became of it."""

    request_id: int
    who: str
    reason: str
    requested_at: datetime
    approved_by: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None


class BreakGlass:
    """Two-person emergency access, time-boxed and fully recorded."""

    def __init__(
        self,
        *,
        window_seconds: int = 900,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        """Start an empty log, with access lasting `window_seconds`."""
        self._window = timedelta(seconds=window_seconds)
        self._now = now
        self._entries: list[Entry] = []

    def request(self, *, who: str, reason: str) -> int:
        """Ask for emergency access, stating why, and get the request id."""
        if not reason.strip():
            raise ValueError("emergency access must say why it is needed")
        entry = Entry(
            request_id=len(self._entries) + 1,
            who=who,
            reason=reason,
            requested_at=self._now(),
        )
        self._entries.append(entry)
        return entry.request_id

    def approve(self, *, request_id: int, by: str) -> None:
        """Approve a request as someone other than the person who raised it."""
        entry = self._find(request_id)
        if entry.who == by:
            raise PermissionError("emergency access needs a second person")
        entry.approved_by = by
        entry.opened_at = self._now()

    def close(self, *, request_id: int) -> None:
        """Close out an approved request."""
        self._find(request_id).closed_at = self._now()

    def active(self) -> tuple[str, ...]:
        """Everyone whose emergency access is open and still in its window."""
        now = self._now()
        return tuple(
            entry.who
            for entry in self._entries
            if entry.opened_at is not None
            and entry.closed_at is None
            and now - entry.opened_at < self._window
        )

    def history(self) -> tuple[Entry, ...]:
        """Every request ever made, in order."""
        return tuple(self._entries)

    def _find(self, request_id: int) -> Entry:
        """The request with this id, or raise if there is none."""
        for entry in self._entries:
            if entry.request_id == request_id:
                return entry
        raise LookupError(f"no request {request_id}")
