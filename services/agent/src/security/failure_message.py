"""Saying what went wrong without saying more than the reader should see."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum

RETRYABLE = {
    "TimeoutError",
    "ConnectionError",
    "ConnectionResetError",
    "RateLimitError",
    "ServiceUnavailable",
}

_STEP = re.compile(r'File "[^"]*/([A-Za-z0-9_]+)\.py"')


class Audience(Enum):
    """Who a failure is being explained to."""

    PERSON = "person"
    OPERATOR = "operator"


@dataclass(frozen=True)
class Explanation:
    """What to say about a failure, and whether it is worth retrying."""

    message: str
    detail: str
    reference: str
    retryable: bool


def explain(failure: str, detail: str, *, audience: Audience) -> Explanation:
    """Explain `failure` in terms suited to `audience`."""
    if not failure.strip():
        raise ValueError("a failure must have a name")

    retryable = failure in RETRYABLE
    step = _step_from(detail)

    message = (
        f"The {step} step could not be completed."
        if step
        else "Something went wrong while running this step."
    )
    if retryable:
        message += " This one often clears on its own — try again in a moment."

    return Explanation(
        message=message,
        detail=detail if audience is Audience.OPERATOR else "",
        reference=hashlib.sha256(f"{failure}\x1f{detail}".encode()).hexdigest()[:12],
        retryable=retryable,
    )


def _step_from(detail: str) -> str:
    """The last step named in a detail string."""
    matches = _STEP.findall(detail)
    return matches[-1] if matches else ""
