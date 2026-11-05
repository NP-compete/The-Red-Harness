"""Choosing which graded items a person should look at."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

PASSING_SCORE = 0.5
CONFIDENT = 0.5


class Reason(Enum):
    """Why an item is worth a person's review."""

    FLAGGED = "flagged"
    DISAGREEMENT = "disagreement"
    LOW_CONFIDENCE = "low_confidence"
    FAILED = "failed"


_ORDER = (Reason.FLAGGED, Reason.DISAGREEMENT, Reason.LOW_CONFIDENCE, Reason.FAILED)


@dataclass(frozen=True)
class Graded:
    """One graded item, and what the graders made of it."""

    item: str
    score: float
    confidence: float
    graders_disagreed: bool
    already_reviewed: bool
    flagged_by_person: bool

    def __post_init__(self) -> None:
        """Reject a score or confidence outside zero to one."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("a score runs from zero to one")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("a confidence runs from zero to one")


@dataclass(frozen=True)
class Entry:
    """One item in the review queue, and why it is there."""

    item: str
    reason: Reason


def _reason_for(graded: Graded) -> Reason | None:
    """Why `graded` needs review, or `None` if it does not."""
    if graded.flagged_by_person:
        return Reason.FLAGGED
    if graded.already_reviewed:
        return None
    if graded.graders_disagreed:
        return Reason.DISAGREEMENT
    if graded.confidence < CONFIDENT:
        return Reason.LOW_CONFIDENCE
    if graded.score < PASSING_SCORE:
        return Reason.FAILED
    return None


def build_queue(results: list[Graded]) -> list[Entry]:
    """Build the review queue from `results`, most pressing first."""
    entries = [
        Entry(item=result.item, reason=reason)
        for result in results
        if (reason := _reason_for(result)) is not None
    ]
    return sorted(entries, key=lambda entry: _ORDER.index(entry.reason))
