"""How much failure is left before risky changes should stop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

AT_RISK_AT = 0.8


class State(Enum):
    """How much of an error budget is left."""

    HEALTHY = "healthy"
    AT_RISK = "at-risk"
    EXHAUSTED = "exhausted"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Budget:
    """An objective and the runs measured against it."""

    objective: float
    total_runs: int
    failed_runs: int

    def __post_init__(self) -> None:
        """Reject an impossible objective or counts that cannot be."""
        if not 0 < self.objective < 1:
            raise ValueError("an objective must leave room for some failure")
        if self.total_runs < 0 or self.failed_runs < 0:
            raise ValueError("counts cannot be negative")
        if self.failed_runs > self.total_runs:
            raise ValueError("more runs failed than ran")


@dataclass(frozen=True)
class Assessment:
    """How much error budget is left, and whether to deploy."""

    state: State
    used: float
    failures_left: int
    may_deploy: bool
    warn: bool
    exceptional: bool
    reason: str = ""


def assess_budget(budget: Budget, *, is_fix: bool = False) -> Assessment:
    """Assess `budget`, allowing more room for a fix."""
    if budget.total_runs == 0:
        return Assessment(
            state=State.UNKNOWN,
            used=0.0,
            failures_left=0,
            may_deploy=True,
            warn=False,
            exceptional=False,
            reason="there is not enough history to judge",
        )

    allowed = budget.total_runs * (1 - budget.objective)
    used = min(1.0, budget.failed_runs / allowed) if allowed > 0 else 1.0
    left = max(0, int(allowed) - budget.failed_runs)

    if used >= 1.0:
        state = State.EXHAUSTED
    elif used >= AT_RISK_AT:
        state = State.AT_RISK
    else:
        state = State.HEALTHY

    spent = state is State.EXHAUSTED

    return Assessment(
        state=state,
        used=used,
        failures_left=left,
        may_deploy=not spent or is_fix,
        warn=state is State.AT_RISK,
        exceptional=spent and is_fix,
        reason="the error budget is spent" if spent else "",
    )
