"""Whether to interrupt a person now, later, or not at all."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum

REPEAT_AFTER = timedelta(hours=1)


class Urgency(Enum):
    """How urgent an event is."""

    NORMAL = "normal"
    URGENT = "urgent"


class When(Enum):
    """When a notification should go out, if at all."""

    NOW = "now"
    LATER = "later"
    NEVER = "never"


@dataclass(frozen=True)
class Preferences:
    """A person's quiet hours and muted notification kinds."""

    quiet_from: time | None
    quiet_until: time | None
    muted_kinds: tuple[str, ...]
    allow_urgent_during_quiet_hours: bool

    def __post_init__(self) -> None:
        """Reject quiet hours given only a start or only an end."""
        if (self.quiet_from is None) != (self.quiet_until is None):
            raise ValueError("quiet hours need both a start and an end")


@dataclass(frozen=True)
class Event:
    """Something that might be notified, and when it last was."""

    kind: str
    urgency: Urgency
    key: str
    last_sent: datetime | None

    def __post_init__(self) -> None:
        """Reject an event with no key to recognise repeats by."""
        if not self.key.strip():
            raise ValueError("an event needs a key so repeats can be recognised")


@dataclass(frozen=True)
class Notification:
    """When a notification goes out, if at all, and why."""

    when: When
    send_at: datetime | None = None
    reason: str = ""


def decide_notification(
    event: Event, preferences: Preferences, *, now: datetime
) -> Notification:
    """Decide whether, and when, `event` should reach the person."""
    if event.kind in preferences.muted_kinds:
        return Notification(When.NEVER, reason=f"{event.kind} is muted")

    if event.last_sent is not None and now - event.last_sent < REPEAT_AFTER:
        return Notification(When.NEVER, reason="this was already sent recently")

    if _is_quiet(now, preferences):
        if (
            event.urgency is Urgency.URGENT
            and preferences.allow_urgent_during_quiet_hours
        ):
            return Notification(When.NOW)
        return Notification(
            When.LATER,
            send_at=_next_time(now, preferences.quiet_until),
            reason="it is outside this person's hours",
        )

    return Notification(When.NOW)


def _is_quiet(now: datetime, preferences: Preferences) -> bool:
    """Whether `now` falls inside the person's quiet hours."""
    start, end = preferences.quiet_from, preferences.quiet_until
    if start is None or end is None:
        return False
    moment = now.timetz().replace(tzinfo=None)
    if start > end:
        return moment >= start or moment < end
    return start <= moment < end


def _next_time(now: datetime, at: time | None) -> datetime | None:
    """The next time of day `at` comes round after `now`."""
    if at is None:
        return None
    candidate = now.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)
