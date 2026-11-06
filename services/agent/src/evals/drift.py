"""Telling a real change in scores apart from ordinary noise."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from statistics import fmean, median

MIN_CASES = 10
MIN_RUNS = 4
OUTLIER_GAP = 0.15
DRIFT = 0.05

WINDOW = 3


class Movement(Enum):
    """Which way scores are going, if it can be told."""

    STEADY = "steady"
    RISING = "rising"
    FALLING = "falling"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Run:
    """One eval run's score over a number of cases."""

    run: str
    score: float
    cases: int

    def __post_init__(self) -> None:
        """Reject a score outside zero to one."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("a score runs from zero to one")


@dataclass(frozen=True)
class Drift:
    """How scores have moved against the baseline."""

    movement: Movement
    gap: float
    outliers: list[str] = field(default_factory=list)

    @property
    def needs_attention(self) -> bool:
        """Whether the movement is bad enough to look at."""
        return self.movement is Movement.FALLING


def detect_drift(history: list[Run], *, baseline: float) -> Drift:
    """Work out which way `history` has moved against `baseline`."""
    if not 0.0 <= baseline <= 1.0:
        raise ValueError("a baseline runs from zero to one")

    counted = [run for run in history if run.cases >= MIN_CASES]
    if len(counted) < MIN_RUNS:
        return Drift(movement=Movement.UNKNOWN, gap=0.0)

    middle = median(run.score for run in counted)
    outliers = [run.run for run in counted if abs(run.score - middle) > OUTLIER_GAP]

    trend = [run for run in counted if run.run not in outliers]
    if len(trend) < MIN_RUNS:
        return Drift(movement=Movement.UNKNOWN, gap=0.0, outliers=outliers)

    early = fmean(run.score for run in trend[:WINDOW])
    recent = fmean(run.score for run in trend[-WINDOW:])
    moved = recent - early

    if moved <= -DRIFT:
        movement = Movement.FALLING
    elif moved >= DRIFT:
        movement = Movement.RISING
    else:
        movement = Movement.STEADY

    return Drift(movement=movement, gap=recent - baseline, outliers=outliers)
