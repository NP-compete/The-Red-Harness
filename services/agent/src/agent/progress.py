"""Saying how far along a long piece of work is, without inventing certainty."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

OVERRUN_FACTOR = 2.0


@dataclass(frozen=True)
class Step:
    """One step of a plan, and how long it took if it is done."""

    name: str
    done: bool
    seconds: float | None

    def __post_init__(self) -> None:
        """Reject a nameless step, or a finished one with no duration."""
        if not self.name.strip():
            raise ValueError("a step must have a name")
        if self.done and self.seconds is None:
            raise ValueError("a finished step must say how long it took")


@dataclass(frozen=True)
class Plan:
    """The steps of a run, and when it started."""

    steps: tuple[Step, ...]
    started_at: datetime
    open_ended: bool

    def __post_init__(self) -> None:
        """Reject an empty plan."""
        if not self.steps:
            raise ValueError("a plan must have something in it")


@dataclass(frozen=True)
class Progress:
    """How far a run has got, and how much longer it may take."""

    doing: str
    done: int
    total: int
    fraction: float | None
    remaining: timedelta | None
    elapsed: timedelta
    total_is_final: bool
    overrunning: bool


def report_progress(plan: Plan, *, now: datetime) -> Progress:
    """Report how far `plan` has got as of `now`."""
    finished = [step for step in plan.steps if step.done]
    outstanding = [step for step in plan.steps if not step.done]
    elapsed = now - plan.started_at

    average = (
        sum(step.seconds or 0.0 for step in finished) / len(finished)
        if finished
        else None
    )

    unknown_total = plan.open_ended

    return Progress(
        doing=outstanding[0].name if outstanding else "",
        done=len(finished),
        total=len(plan.steps),
        fraction=None if unknown_total else len(finished) / len(plan.steps),
        remaining=(
            None
            if unknown_total or average is None
            else timedelta(seconds=average * len(outstanding))
        ),
        elapsed=elapsed,
        total_is_final=not plan.open_ended,
        overrunning=(
            average is not None
            and elapsed.total_seconds() > average * len(plan.steps) * OVERRUN_FACTOR
        ),
    )
