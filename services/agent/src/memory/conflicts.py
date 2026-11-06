"""Reconciling something newly learned with what is already remembered."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum

STALE_AFTER = timedelta(days=180)
REINFORCEMENT = 0.1
STATED = "stated"


class Resolution(Enum):
    """What happened when a new memory met an existing one."""

    ADDED = "added"
    UNCHANGED = "unchanged"
    SUPERSEDED = "superseded"
    KEPT_EXISTING = "kept-existing"


@dataclass(frozen=True)
class Memory:
    """One remembered fact, where it came from and how sure it is."""

    key: str
    value: str
    learned_at: datetime
    source: str
    confidence: float

    def __post_init__(self) -> None:
        """Reject a memory about nothing, or confidence outside zero to one."""
        if not self.key.strip():
            raise ValueError("a memory must be about something")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence runs from nothing to certainty")


@dataclass(frozen=True)
class Reconciliation:
    """Which memory was kept, and whether to mention the change."""

    resolution: Resolution
    kept: Memory
    replaced: str = ""
    worth_mentioning: bool = False
    reason: str = ""


def reconcile(new: Memory, *, existing: Memory | None, now: datetime) -> Reconciliation:
    """Reconcile `new` against `existing` as of `now`."""
    if existing is None:
        return Reconciliation(Resolution.ADDED, kept=new)

    if existing.key != new.key:
        raise ValueError("two memories about different things cannot be reconciled")

    if existing.value == new.value:
        return Reconciliation(
            Resolution.UNCHANGED,
            kept=replace(
                existing, confidence=min(1.0, existing.confidence + REINFORCEMENT)
            ),
        )

    if _supersedes(new, existing, now=now):
        return Reconciliation(
            Resolution.SUPERSEDED,
            kept=new,
            replaced=existing.value,
            worth_mentioning=True,
            reason=f"this replaces {existing.value}",
        )

    return Reconciliation(
        Resolution.KEPT_EXISTING,
        kept=existing,
        worth_mentioning=True,
        reason=f"{existing.value} was stated, so a guess does not replace it",
    )


def _supersedes(new: Memory, existing: Memory, *, now: datetime) -> bool:
    """Whether `new` should replace `existing`."""
    if now - existing.learned_at > STALE_AFTER:
        return True
    if existing.source == STATED and new.source != STATED:
        return False
    if new.source == STATED and existing.source != STATED:
        return True
    if new.source == existing.source == STATED:
        return new.learned_at >= existing.learned_at
    return new.confidence > existing.confidence
