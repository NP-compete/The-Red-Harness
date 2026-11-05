"""Verifying a signature while an old key is still being retired."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Status(Enum):
    """How a signature verified, if it did."""

    VERIFIED = "verified"
    VERIFIED_WITH_OLD_KEY = "verified-with-old-key"
    NOT_VERIFIED = "not-verified"


@dataclass(frozen=True)
class Key:
    """One signing key and whether it is retired or compromised."""

    id: str
    secret: str
    retired_at: datetime | None
    compromised: bool

    def __post_init__(self) -> None:
        """Reject a key with no identifier or no secret."""
        if not self.id.strip():
            raise ValueError("a key must have an identifier")
        if not self.secret:
            raise ValueError("a key must have a secret")


@dataclass(frozen=True)
class Keyring:
    """The current signing key and the previous ones still honoured."""

    current: Key
    previous: tuple[Key, ...] = ()

    def __post_init__(self) -> None:
        """Reject a keyring holding the same key id twice."""
        ids = [self.current.id, *(key.id for key in self.previous)]
        if len(ids) != len(set(ids)):
            raise ValueError("a keyring cannot hold the same key twice")


@dataclass(frozen=True)
class Verification:
    """How a signature verified, and against which key."""

    status: Status
    key_id: str = ""
    reason: str = ""


def verify_with(
    keyring: Keyring, body: bytes, signature: str, *, now: datetime
) -> Verification:
    """Verify `signature` over `body` against the keyring as of `now`."""
    if _matches(keyring.current, body, signature):
        return Verification(Status.VERIFIED, keyring.current.id)

    for key in keyring.previous:
        if key.retired_at is not None and now >= key.retired_at:
            continue
        if _matches(key, body, signature):
            return Verification(
                Status.VERIFIED_WITH_OLD_KEY,
                key.id,
                f"{key.id} is being retired; rotate the sender to {keyring.current.id}",
            )

    withdrawn = any(key.compromised for key in (keyring.current, *keyring.previous))
    return Verification(
        Status.NOT_VERIFIED,
        reason="a withdrawn key was used"
        if withdrawn
        else "the signature did not match",
    )


def _matches(key: Key, body: bytes, signature: str) -> bool:
    """Whether `signature` is this key's HMAC over `body`."""
    if key.compromised or not signature:
        return False
    expected = hmac.new(key.secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
