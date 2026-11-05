"""Request signature verification for inbound channels."""

from __future__ import annotations

import hashlib
import hmac
import math
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    """Whether a signature checked out, and why not when it did not."""

    ok: bool
    reason: str = ""

    def __bool__(self) -> bool:
        """Truthy when verification passed, so callers can use `if result:`."""
        return self.ok


def _fresh(timestamp: str, max_age_seconds: int, now: float) -> VerificationResult:
    try:
        sent_at = float(timestamp)
    except (TypeError, ValueError):
        return VerificationResult(False, "timestamp is not a number")

    if not math.isfinite(sent_at):
        return VerificationResult(False, "timestamp is not a finite number")

    age = now - sent_at
    if age > max_age_seconds:
        return VerificationResult(False, f"timestamp too old ({int(age)}s)")
    if age < -max_age_seconds:
        return VerificationResult(
            False, f"timestamp too far in the future ({int(-age)}s)"
        )
    return VerificationResult(True)


def verify_slack(
    *,
    body: bytes,
    timestamp: str,
    signature: str,
    secret: str,
    max_age_seconds: int = 300,
    now: float | None = None,
) -> VerificationResult:
    """Verify Slack's v0 request signature."""
    if not secret:
        return VerificationResult(False, "no signing secret configured")
    if not signature or not timestamp:
        return VerificationResult(False, "missing signature or timestamp header")

    fresh = _fresh(timestamp, max_age_seconds, time.time() if now is None else now)
    if not fresh:
        return fresh

    basestring = b"v0:" + timestamp.encode() + b":" + body
    digest = hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"

    if not hmac.compare_digest(expected.encode(), signature.encode("utf-8", "replace")):
        return VerificationResult(False, "signature mismatch")
    return VerificationResult(True)


def verify_webhook(
    *,
    body: bytes,
    timestamp: str,
    signature: str,
    secret: str,
    max_age_seconds: int = 300,
    now: float | None = None,
) -> VerificationResult:
    """Verify the generic webhook signature."""
    if not secret:
        return VerificationResult(False, "no signing secret configured")
    if not signature or not timestamp:
        return VerificationResult(False, "missing signature or timestamp header")

    fresh = _fresh(timestamp, max_age_seconds, time.time() if now is None else now)
    if not fresh:
        return fresh

    basestring = timestamp.encode() + b"." + body
    digest = hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
    candidate = signature[7:] if signature.startswith("sha256=") else signature

    if not hmac.compare_digest(digest, candidate):
        return VerificationResult(False, "signature mismatch")
    return VerificationResult(True)


def sign_webhook(*, body: bytes, timestamp: str, secret: str) -> str:
    """Produce a signature the way a sender would."""
    basestring = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
