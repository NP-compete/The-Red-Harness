"""Moving a new version into service one share of traffic at a time."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MIN_RUNS = 50
FAILURE_TOLERANCE = 0.02
MAX_REFUSAL_RATE = 0.25


class Step(Enum):
    """What happened to a rollout on this check."""

    ADVANCED = "advanced"
    COMPLETE = "complete"
    WAITING = "waiting"
    HALTED = "halted"
    ROLLED_BACK = "rolled-back"


@dataclass(frozen=True)
class Health:
    """How the new version is faring against the baseline."""

    runs: int
    failure_rate: float
    refusal_rate: float
    baseline_failure_rate: float


@dataclass(frozen=True)
class Rollout:
    """A version being rolled out, and the shares it climbs through."""

    version: str
    previous_version: str
    share: float
    steps: tuple[float, ...]
    halted: bool = False

    def __post_init__(self) -> None:
        """Reject a rollout that replaces itself or whose steps do not climb."""
        if self.version == self.previous_version:
            raise ValueError("a version cannot replace itself")
        if not self.steps:
            raise ValueError("a rollout needs at least one step")
        if any(b <= a for a, b in zip(self.steps, self.steps[1:])):
            raise ValueError("rollout steps must climb")
        if not 0 < self.steps[-1] <= 1.0:
            raise ValueError("the last rollout step must serve everyone")


@dataclass(frozen=True)
class Advance:
    """The share to serve next, and why."""

    step: Step
    share: float
    reason: str = ""


def advance(rollout: Rollout, health: Health) -> Advance:
    """Decide whether to widen, hold, or roll back a rollout."""
    harm = _harm(health)
    if harm:
        return Advance(
            Step.ROLLED_BACK,
            0.0,
            f"{harm}; serving {rollout.previous_version} again",
        )

    if health.runs < MIN_RUNS:
        return Advance(
            Step.WAITING,
            rollout.share,
            f"{health.runs} runs so far; more runs are needed before moving on",
        )

    if rollout.halted:
        return Advance(Step.HALTED, rollout.share, "this rollout is held where it is")

    nxt = next((step for step in rollout.steps if step > rollout.share), None)
    if nxt is None:
        return Advance(Step.COMPLETE, rollout.steps[-1])

    return Advance(Step.COMPLETE if nxt >= 1.0 else Step.ADVANCED, nxt)


def _harm(health: Health) -> str:
    """The harm the new version is doing, or an empty string if none."""
    if health.runs < MIN_RUNS:
        return ""
    if health.failure_rate > health.baseline_failure_rate + FAILURE_TOLERANCE:
        return f"failures rose from {health.baseline_failure_rate:.0%} to {health.failure_rate:.0%}"
    if health.refusal_rate > MAX_REFUSAL_RATE:
        return f"{health.refusal_rate:.0%} of runs were refused"
    return ""
