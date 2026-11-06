"""What someone from outside the organisation may do once invited in."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

GUEST_MAY = {"read", "write"}


@dataclass(frozen=True)
class Guest:
    """Someone invited from outside, and what they were invited to."""

    person: str
    invited_to: tuple[str, ...]
    expires_at: datetime | None
    accepted: bool
    may_write: bool

    def __post_init__(self) -> None:
        """Reject an invitation to nothing, or one that never expires."""
        if not self.invited_to:
            raise ValueError("an invitation must be to something")
        if self.expires_at is None:
            raise ValueError("an invitation from outside must end")
        if self.expires_at.tzinfo is None:
            raise ValueError("an expiry needs a zone")


@dataclass(frozen=True)
class Want:
    """What a guest is trying to do."""

    action: str
    thread: str


@dataclass(frozen=True)
class Decided:
    """Whether a guest may do it, and how long they have left."""

    allowed: bool
    reason: str
    days_left: int


def may_guest(guest: Guest, *, want: Want, now: datetime) -> Decided:
    """Decide whether `guest` may do `want` as of `now`."""
    expires_at = guest.expires_at
    assert expires_at is not None  # Guest.__post_init__ rules this out
    left = max(0, (expires_at - now).days)

    def no(reason: str) -> Decided:
        """A refusal with this reason."""
        return Decided(allowed=False, reason=reason, days_left=left)

    if not guest.accepted:
        return no("this invitation has not been accepted")
    if expires_at <= now:
        return no("this invitation has expired")
    if want.thread not in guest.invited_to:
        return no("this guest was not invited to that conversation")
    if want.action not in GUEST_MAY:
        return no(f"a guest cannot {want.action}")
    if want.action == "write" and not guest.may_write:
        return no("this guest was invited to read, not to reply")

    return Decided(allowed=True, reason="", days_left=left)
