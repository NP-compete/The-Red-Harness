"""Letting an administrator act as someone else, briefly and on the record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

MAX_SESSION = timedelta(hours=4)
MIN_REASON = 10
ALLOWED_ROLES = {"support", "platform-admin"}


class Refusal(Enum):
    """Why an impersonation session was not started."""

    NO_CONSENT = "no-consent"
    CONSENT_EXPIRED = "consent-expired"
    WRONG_SUBJECT = "wrong-subject"
    NOT_PERMITTED = "not-permitted"
    SELF = "self"
    NO_REASON = "no-reason"


@dataclass(frozen=True)
class Grant:
    """A person's consent to be impersonated, and when it lapses."""

    subject: str
    granted_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        """Reject a grant that names nobody or lasts no time."""
        if not self.subject.strip():
            raise ValueError("a grant must name who gave it")
        if self.expires_at <= self.granted_at:
            raise ValueError("a grant must last some time")


@dataclass(frozen=True)
class Request:
    """An administrator's request to act as someone else."""

    administrator: str
    subject: str
    reason: str
    consent: Grant | None
    administrator_roles: tuple[str, ...]


@dataclass(frozen=True)
class Session:
    """An impersonation session, or the refusal that stopped it."""

    permitted: bool
    acting_as: str = ""
    really: str = ""
    expires_at: datetime | None = None
    read_only: bool = True
    may_impersonate: bool = False
    reason: str = ""
    refusal: Refusal | None = None


def begin_impersonation(
    request: Request, *, now: datetime, read_only: bool = True
) -> Session:
    """Start an impersonation session, or refuse with a reason."""

    def refuse(refusal: Refusal) -> Session:
        """A refused session carrying this code."""
        return Session(permitted=False, refusal=refusal, really=request.administrator)

    if request.administrator == request.subject:
        return refuse(Refusal.SELF)

    if not set(request.administrator_roles) & ALLOWED_ROLES:
        return refuse(Refusal.NOT_PERMITTED)

    if len(request.reason.strip()) < MIN_REASON:
        return refuse(Refusal.NO_REASON)

    if request.consent is None:
        return refuse(Refusal.NO_CONSENT)

    if request.consent.subject != request.subject:
        return refuse(Refusal.WRONG_SUBJECT)

    if now >= request.consent.expires_at:
        return refuse(Refusal.CONSENT_EXPIRED)

    return Session(
        permitted=True,
        acting_as=request.subject,
        really=request.administrator,
        expires_at=min(request.consent.expires_at, now + MAX_SESSION),
        read_only=read_only,
        may_impersonate=False,
        reason=request.reason.strip(),
    )
