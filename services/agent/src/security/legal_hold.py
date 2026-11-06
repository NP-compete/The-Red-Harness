"""Holds that keep data a deletion would otherwise remove."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Hold:
    """One legal hold: what it covers, who placed it, and when it lifted."""

    reference: str
    subjects: tuple[str, ...]
    placed_by: str
    lifted_at: datetime | None

    def __post_init__(self) -> None:
        """Reject a hold that names nobody or no placer."""
        if not self.placed_by.strip():
            raise ValueError("a hold must say who placed it")
        if not self.subjects:
            raise ValueError("a hold must name whose data it covers")


class Holds:
    """Every legal hold, answering what may not be deleted."""

    def __init__(
        self,
        holds: list[Hold],
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        """Bind to `holds`, reading the current time from `now`."""
        self._holds = holds
        self._now = now

    def covers(self, subject: str) -> bool:
        """Whether any live hold covers `subject`."""
        return bool(self.references(subject))

    def references(self, subject: str) -> tuple[str, ...]:
        """The references of every live hold covering `subject`."""
        now = self._now()
        return tuple(
            hold.reference
            for hold in self._holds
            if subject in hold.subjects
            and (hold.lifted_at is None or hold.lifted_at > now)
        )

    def check_deletion(self, subject: str) -> None:
        """Raise if `subject`'s data is under a live hold."""
        active = self.references(subject)
        if active:
            raise PermissionError(
                f"data for {subject} is held under {', '.join(active)} and cannot be deleted"
            )
