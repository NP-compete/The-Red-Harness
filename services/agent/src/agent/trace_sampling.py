"""Deciding which finished traces are worth keeping."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

BUCKETS = 10_000


class Reason(Enum):
    """Why a trace was kept or dropped."""

    FAILED = "failed"
    SLOW = "slow"
    COSTLY = "costly"
    APPROVED = "approved"
    SAMPLED = "sampled"
    NOT_SAMPLED = "not-sampled"


@dataclass(frozen=True)
class Finished:
    """A finished trace and everything that bears on keeping it."""

    trace_id: str
    failed: bool
    duration_ms: float
    approved_step: bool
    cost: float
    sample_rate: float
    slow_above_ms: float
    costly_above: float

    def __post_init__(self) -> None:
        """Reject a trace with no id, a bad sample rate, or negative figures."""
        if not self.trace_id.strip():
            raise ValueError("a trace must have an identifier")
        if not 0 <= self.sample_rate <= 1:
            raise ValueError("a sample rate runs from nothing to everything")
        if self.duration_ms < 0 or self.cost < 0:
            raise ValueError("a trace cannot take or cost less than nothing")


@dataclass(frozen=True)
class Decision:
    """Whether to keep a trace, and why."""

    keep: bool
    reason: Reason


def should_keep(trace: Finished) -> Decision:
    """Decide whether `trace` is worth keeping."""
    if trace.failed:
        return Decision(True, Reason.FAILED)
    if trace.duration_ms > trace.slow_above_ms:
        return Decision(True, Reason.SLOW)
    if trace.cost > trace.costly_above:
        return Decision(True, Reason.COSTLY)
    if trace.approved_step:
        return Decision(True, Reason.APPROVED)

    digest = hashlib.sha256(trace.trace_id.encode()).digest()
    bucket = int.from_bytes(digest[:4], "big") % BUCKETS

    if bucket < trace.sample_rate * BUCKETS:
        return Decision(True, Reason.SAMPLED)
    return Decision(False, Reason.NOT_SAMPLED)
