"""Whether there is time left in the run to take another step."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

ASSUMED_STEP = timedelta(seconds=60)
WARN_FRACTION = 0.1


class Outcome(Enum):
    """Whether a run has time for another step."""

    CONTINUE = "continue"
    STEP_TOO_LONG = "step-too-long"
    OUT_OF_TIME = "out-of-time"


@dataclass(frozen=True)
class TimeBudget:
    """How long a run may take, and the reserve kept back to finish up."""

    started_at: datetime
    limit: timedelta | None
    reserve: timedelta

    def __post_init__(self) -> None:
        """Reject a budget of no time, or a reserve as big as the whole."""
        if self.limit is None:
            return
        if self.limit <= timedelta(0):
            raise ValueError("a run needs some time to run in")
        if self.reserve >= self.limit:
            raise ValueError("the reserve cannot be the whole budget")


@dataclass(frozen=True)
class Decision:
    """Whether to go on, how long is left, and whether to warn."""

    outcome: Outcome
    remaining: timedelta | None
    warn: bool
    failed: bool = False
    reason: str = ""


def may_continue(
    budget: TimeBudget, *, expected_step: timedelta | None, now: datetime
) -> Decision:
    """Decide whether a step expected to take `expected_step` still fits."""
    if budget.limit is None:
        return Decision(Outcome.CONTINUE, remaining=None, warn=False)

    remaining = budget.started_at + budget.limit - now
    warn = remaining <= budget.limit * WARN_FRACTION

    if remaining <= timedelta(0):
        return Decision(
            Outcome.OUT_OF_TIME,
            remaining=remaining,
            warn=True,
            reason="this run has used all the time it was given",
        )

    step = expected_step if expected_step is not None else ASSUMED_STEP
    if step > remaining - budget.reserve:
        return Decision(
            Outcome.STEP_TOO_LONG,
            remaining=remaining,
            warn=warn,
            reason=(
                f"the next step needs about {int(step.total_seconds())}s "
                f"and only {int(remaining.total_seconds())}s remain"
            ),
        )

    return Decision(Outcome.CONTINUE, remaining=remaining, warn=warn)
