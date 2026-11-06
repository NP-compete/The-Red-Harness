"""How long a thread is kept before it is archived or thrown away."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

WARN_DAYS = 7


class Action(Enum):
    """What should happen to a thread."""

    KEEP = "keep"
    ARCHIVE = "archive"
    DELETE = "delete"


@dataclass(frozen=True)
class RetentionRules:
    """How long threads are kept, overall and per classification."""

    keep_days: int
    archive_after_days: int
    keep_days_by_classification: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject negative retention, or deletion before archival."""
        if self.keep_days < 0 or self.archive_after_days < 0:
            raise ValueError("retention cannot be negative")
        if self.keep_days and self.archive_after_days > self.keep_days:
            raise ValueError("a thread cannot be deleted before it is archived")

    def keep_days_for(self, classification: str) -> int:
        """How many days a thread of this classification is kept."""
        return self.keep_days_by_classification.get(classification, self.keep_days)


@dataclass(frozen=True)
class Thread:
    """The facts about a thread that bear on how long it is kept."""

    last_activity: datetime
    classification: str
    on_legal_hold: bool = False
    pinned: bool = False


@dataclass(frozen=True)
class Retention:
    """What to do with a thread, when, and whether to warn first."""

    action: Action
    delete_on: datetime | None
    warn: bool
    reason: str = ""


def decide_retention(
    thread: Thread, rules: RetentionRules, *, now: datetime
) -> Retention:
    """Decide what happens to `thread` under `rules` as of `now`."""
    if thread.on_legal_hold:
        return Retention(
            action=Action.KEEP,
            delete_on=None,
            warn=False,
            reason="this thread is under a legal hold",
        )

    keep_days = rules.keep_days_for(thread.classification)
    age = (now - thread.last_activity).days
    delete_on = (
        thread.last_activity + timedelta(days=keep_days)
        if keep_days and not thread.pinned
        else None
    )

    if keep_days and age >= keep_days:
        if thread.pinned:
            return Retention(Action.KEEP, None, False, "this thread is pinned")
        return Retention(Action.DELETE, delete_on, False, f"no activity for {age} days")

    if rules.archive_after_days and age >= rules.archive_after_days:
        return Retention(
            action=Action.ARCHIVE,
            delete_on=delete_on,
            warn=_warn(delete_on, now),
            reason=f"no activity for {age} days",
        )

    return Retention(Action.KEEP, delete_on, _warn(delete_on, now))


def _warn(delete_on: datetime | None, now: datetime) -> bool:
    """Whether deletion is close enough to warn about."""
    return delete_on is not None and (delete_on - now) <= timedelta(days=WARN_DAYS)
