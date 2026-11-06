"""Getting back what someone had typed but not sent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

KEEP_FOR = timedelta(days=7)


class Outcome(Enum):
    """What became of a recovered draft."""

    OFFERED = "offered"
    ALREADY_SENT = "already-sent"
    NOTHING_TO_RECOVER = "nothing-to-recover"
    TOO_OLD = "too-old"
    THREAD_GONE = "thread-gone"


@dataclass(frozen=True)
class Draft:
    """An unsent draft, when it was saved and whether it was sent."""

    thread: str
    text: str
    saved_at: datetime
    attachments: tuple[str, ...] = ()
    sent_at: datetime | None = None

    def __post_init__(self) -> None:
        """Reject a draft with no thread, or sent before it was written."""
        if not self.thread.strip():
            raise ValueError("a draft must belong to a thread")
        if self.sent_at is not None and self.sent_at < self.saved_at:
            raise ValueError("a draft cannot be sent before it was written")


@dataclass(frozen=True)
class Recovered:
    """The recovered draft, its age, and when it stops being kept."""

    outcome: Outcome
    text: str
    attachments: tuple[str, ...]
    age: timedelta
    expires_at: datetime
    reason: str = ""


def recover_draft(
    draft: Draft, *, now: datetime, thread_exists: bool = True
) -> Recovered:
    """Decide whether `draft` can still be offered back as of `now`."""
    age = max(timedelta(0), now - draft.saved_at)
    expires_at = draft.saved_at + KEEP_FOR

    def result(outcome: Outcome, *, text: str, reason: str = "") -> Recovered:
        """A recovery outcome carrying this text and reason."""
        return Recovered(
            outcome=outcome,
            text=text,
            attachments=draft.attachments if text or draft.attachments else (),
            age=age,
            expires_at=expires_at,
            reason=reason,
        )

    if draft.sent_at is not None:
        return result(Outcome.ALREADY_SENT, text="")

    if not draft.text.strip() and not draft.attachments:
        return result(Outcome.NOTHING_TO_RECOVER, text="")

    if age > KEEP_FOR:
        return result(
            Outcome.TOO_OLD, text="", reason="this draft is too old to offer back"
        )

    if not thread_exists:
        return result(
            Outcome.THREAD_GONE,
            text=draft.text,
            reason="the conversation this belonged to is gone",
        )

    return result(Outcome.OFFERED, text=draft.text, reason=f"saved {_ago(age)} ago")


def _ago(age: timedelta) -> str:
    """`age` rendered in the largest sensible unit."""
    seconds = int(age.total_seconds())
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        return f"{seconds // 60} minutes"
    if seconds < 86_400:
        return f"{seconds // 3600} hours"
    return f"{seconds // 86_400} days"
