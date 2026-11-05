"""Whether a session is still good, and whether to ask who it is again."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

REAUTH_WINDOW = timedelta(minutes=15)
WARN_BEFORE = timedelta(minutes=5)


class State(Enum):
    """Where a session stands against its limits."""

    LIVE = "live"
    IDLE_EXPIRED = "idle-expired"
    EXPIRED = "expired"
    REAUTH_NEEDED = "reauth-needed"


@dataclass(frozen=True)
class Session:
    """When a session started, was last seen, and when it must end."""

    started_at: datetime
    last_seen_at: datetime
    authenticated_at: datetime
    idle_limit: timedelta
    absolute_limit: timedelta

    def __post_init__(self) -> None:
        """Reject a session seen before it started, or outlasting its own limit."""
        if self.last_seen_at < self.started_at:
            raise ValueError("a session cannot be seen before it starts")
        if self.idle_limit > self.absolute_limit:
            raise ValueError("an idle limit cannot outlast the session itself")


@dataclass(frozen=True)
class Check:
    """Whether a session is still usable, and when it lapses."""

    state: State
    usable: bool
    session_still_valid: bool
    warn: bool = False
    idle_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str = ""


def check_session(session: Session, *, now: datetime, sensitive: bool = False) -> Check:
    """Judge `session` against its limits as of `now`."""
    ends_at = session.started_at + session.absolute_limit
    idle_at = session.last_seen_at + session.idle_limit

    def closed(state: State, reason: str) -> Check:
        """A check for a session that is over."""
        return Check(state, usable=False, session_still_valid=False, reason=reason)

    if now >= ends_at:
        return closed(State.EXPIRED, "this session has reached its maximum length")

    if now >= idle_at:
        return closed(State.IDLE_EXPIRED, "this session has been idle too long")

    if session.last_seen_at > now:
        return closed(State.EXPIRED, "this session's activity is dated in the future")

    if sensitive and now - session.authenticated_at > REAUTH_WINDOW:
        return Check(
            State.REAUTH_NEEDED,
            usable=False,
            session_still_valid=True,
            idle_at=idle_at,
            ends_at=ends_at,
            reason="this action needs a recent sign-in",
        )

    return Check(
        State.LIVE,
        usable=True,
        session_still_valid=True,
        warn=idle_at - now <= WARN_BEFORE,
        idle_at=idle_at,
        ends_at=ends_at,
    )
