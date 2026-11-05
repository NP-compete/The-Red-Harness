"""Signing outbound requests, and checking one that comes back."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_SECRET = 16
MAX_AGE = timedelta(minutes=5)
DRIFT = timedelta(seconds=30)


@dataclass(frozen=True)
class SigningKey:
    """A key for signing requests."""

    id: str
    secret: str

    def __post_init__(self) -> None:
        """Reject a key with no identifier or too short a secret."""
        if not self.id.strip():
            raise ValueError("a signing key must have an identifier")
        if len(self.secret) < MIN_SECRET:
            raise ValueError("a signing secret must be long enough to be worth having")


@dataclass(frozen=True)
class SignedRequest:
    """A signature over a request body, and when it was made."""

    key_id: str
    signed_at: datetime
    signature: str


@dataclass(frozen=True)
class Verification:
    """Whether a signature verified, and why not."""

    verified: bool
    reason: str = ""


def sign_request(body: bytes, *, key: SigningKey, now: datetime) -> SignedRequest:
    """Sign `body` with `key` at `now`."""
    return SignedRequest(
        key_id=key.id,
        signed_at=now,
        signature=_signature(body, key=key, at=now),
    )


def verify_signed(
    body: bytes, signed: SignedRequest, *, key: SigningKey, now: datetime
) -> Verification:
    """Verify `signed` over `body`, rejecting one too old or too far ahead."""
    age = now - signed.signed_at

    if age > MAX_AGE:
        return Verification(False, "this request is too old to accept")
    if age < -DRIFT:
        return Verification(False, "this request is dated too far ahead")

    expected = _signature(body, key=key, at=signed.signed_at)
    if not hmac.compare_digest(expected, signed.signature):
        return Verification(False, "the signature did not match")

    return Verification(True)


def _signature(body: bytes, *, key: SigningKey, at: datetime) -> str:
    """The HMAC over the timestamp and body."""
    message = at.isoformat().encode() + b"\x1f" + body
    return hmac.new(key.secret.encode(), message, hashlib.sha256).hexdigest()
