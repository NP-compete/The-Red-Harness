"""Tokens people create so their own code can call the platform."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

SECRET_BYTES = 32
HINT_LENGTH = 6
MAX_LIFETIME = timedelta(days=365)


class Refusal(Enum):
    """Why a token was not accepted."""

    REVOKED = "revoked"
    EXPIRED = "expired"
    NOT_VALID = "not-valid"
    SCOPE_MISSING = "scope-missing"


@dataclass(frozen=True)
class Request:
    """A request to issue a token, and the scopes the owner can delegate."""

    owner: str
    name: str
    scopes: tuple[str, ...]
    owner_scopes: tuple[str, ...]
    lifetime: timedelta | None


@dataclass(frozen=True)
class Token:
    """An issued token, stored as a digest with a display hint."""

    id: str
    owner: str
    name: str
    scopes: tuple[str, ...]
    hint: str
    digest: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class Issued:
    """A freshly issued token and the secret, shown only once."""

    token: Token
    secret: str


@dataclass(frozen=True)
class Verification:
    """Whether a presented token is good for what was asked."""

    permitted: bool
    refusal: Refusal | None = None
    reason: str = ""


def issue(request: Request, *, now: datetime) -> Issued:
    """Issue a token for `request`, returning it with its one-time secret."""
    if not request.name.strip():
        raise ValueError("a token must have a name")
    if not request.scopes:
        raise ValueError("a token with no scopes can do nothing")
    if request.lifetime is None:
        raise ValueError("a token must expire")
    if request.lifetime > MAX_LIFETIME:
        raise ValueError("a token cannot outlast the ceiling")

    beyond = set(request.scopes) - set(request.owner_scopes)
    if beyond:
        raise ValueError(
            f"a token cannot exceed its owner: {', '.join(sorted(beyond))}"
        )

    secret = secrets.token_urlsafe(SECRET_BYTES)

    return Issued(
        token=Token(
            id=secrets.token_hex(8),
            owner=request.owner,
            name=request.name,
            scopes=tuple(request.scopes),
            hint=secret[:HINT_LENGTH],
            digest=_digest(secret),
            created_at=now,
            expires_at=now + request.lifetime,
        ),
        secret=secret,
    )


def verify(secret: str, token: Token, *, need: str, now: datetime) -> Verification:
    """Check `secret` against `token` and confirm it carries the `need` scope."""
    if token.revoked_at is not None and now >= token.revoked_at:
        return Verification(False, Refusal.REVOKED, "this token has been revoked")

    if now >= token.expires_at:
        return Verification(False, Refusal.EXPIRED, "this token has expired")

    if not hmac.compare_digest(_digest(secret), token.digest):
        return Verification(False, Refusal.NOT_VALID, "this token is not valid")

    if need not in token.scopes:
        return Verification(
            False, Refusal.SCOPE_MISSING, f"this token does not grant {need}"
        )

    return Verification(True)


def _digest(secret: str) -> str:
    """The stored digest of a token secret."""
    return hashlib.sha256(secret.encode()).hexdigest()
