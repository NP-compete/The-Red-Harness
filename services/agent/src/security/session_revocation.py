"""Cutting off sessions that should no longer work."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Verdict(Enum):
    """Whether a session is still good."""

    VALID = "valid"
    REVOKED = "revoked"


@dataclass(frozen=True)
class Session:
    """One signed-in session."""

    session_id: str
    person: str
    issued_at: datetime
    device: str = ""

    def __post_init__(self) -> None:
        """Reject a session with no identifier."""
        if not self.session_id.strip():
            raise ValueError("a session must have an identifier")


@dataclass(frozen=True)
class Revocation:
    """An order revoking a session, or everything issued to a person."""

    session_id: str
    person: str
    issued_at: datetime
    reason: str
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        """Reject a revocation that names nobody or gives no reason."""
        if not self.session_id.strip() and not self.person.strip():
            raise ValueError("a revocation must name a session or a person")
        if not self.reason.strip():
            raise ValueError("a revocation must say why")


@dataclass(frozen=True)
class Check:
    """The outcome of testing a session against the revocations."""

    verdict: Verdict
    must_sign_in_again: bool
    reason: str = ""


def check_revoked(
    session: Session, *, revocations: tuple[Revocation, ...], now: datetime
) -> Check:
    """Decide whether `session` has been revoked as of `now`."""
    for revocation in revocations:
        if revocation.expires_at is not None and now >= revocation.expires_at:
            continue

        if revocation.session_id and revocation.session_id == session.session_id:
            return Check(Verdict.REVOKED, True, revocation.reason)

        if (
            revocation.person
            and revocation.person == session.person
            and session.issued_at <= revocation.issued_at
        ):
            return Check(Verdict.REVOKED, True, revocation.reason)

    return Check(Verdict.VALID, False)
