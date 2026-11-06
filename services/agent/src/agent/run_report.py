"""Telling someone what a run did, once it has finished."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from enum import Enum


class Outcome(Enum):
    """How a run ended."""

    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass(frozen=True)
class Ending:
    """How a run finished, what it cost, and what it changed."""

    finished: bool
    steps_done: int
    steps_total: int
    elapsed: timedelta
    cost: Decimal
    changes: tuple[str, ...]
    permanent_changes: tuple[str, ...]
    unanswered_parts: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    failed_step: str
    stopped_by: str

    def __post_init__(self) -> None:
        """Reject an unfinished run that does not say why."""
        if not self.finished and not (self.failed_step or self.stopped_by):
            raise ValueError("a run that did not finish must say why")


@dataclass(frozen=True)
class Report:
    """What to tell the person about a finished run."""

    outcome: Outcome
    headline: str
    took: str
    cost: Decimal
    changes: tuple[str, ...]
    permanent: tuple[str, ...]
    gaps: tuple[str, ...]
    unsupported: tuple[str, ...]
    reversible: bool
    needs_attention: bool


def build_report(ending: Ending) -> Report:
    """Build the report for a run that has ended."""
    outcome, headline = _outcome(ending)
    gaps = ending.unanswered_parts
    unsupported = ending.unsupported_claims

    return Report(
        outcome=outcome,
        headline=headline,
        took=_took(ending.elapsed),
        cost=ending.cost,
        changes=ending.changes,
        permanent=ending.permanent_changes,
        gaps=gaps,
        unsupported=unsupported,
        reversible=bool(ending.changes) and not ending.permanent_changes,
        needs_attention=outcome is not Outcome.DONE,
    )


def _outcome(ending: Ending) -> tuple[Outcome, str]:
    """The outcome and headline for how a run ended."""
    if ending.failed_step:
        return Outcome.FAILED, f"Stopped at {ending.failed_step}, which failed"
    if ending.stopped_by:
        return (
            Outcome.STOPPED,
            f"Stopped by {ending.stopped_by} after {ending.steps_done} steps",
        )
    if ending.unanswered_parts or ending.unsupported_claims:
        return (
            Outcome.PARTIAL,
            "Finished, but part of this is unanswered or unsupported",
        )
    return Outcome.DONE, f"Finished all {ending.steps_total} steps"


def _took(elapsed: timedelta) -> str:
    seconds = int(elapsed.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"
