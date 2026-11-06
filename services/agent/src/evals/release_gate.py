"""Deciding whether a change may be released."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Blocker(Enum):
    """One thing standing in the way of a release."""

    REGRESSED = "regressed"
    UNRELIABLE_SUITE = "unreliable-suite"
    UNPROVEN_JUDGE = "unproven-judge"
    WEAK_DATASET = "weak-dataset"
    BUDGET_SPENT = "budget-spent"


ORDER = (
    Blocker.REGRESSED,
    Blocker.UNRELIABLE_SUITE,
    Blocker.UNPROVEN_JUDGE,
    Blocker.WEAK_DATASET,
    Blocker.BUDGET_SPENT,
)

NEXT_STEP = {
    Blocker.REGRESSED: "fix the broken cases or accept them deliberately",
    Blocker.UNRELIABLE_SUITE: "steady the suite before letting it decide",
    Blocker.UNPROVEN_JUDGE: "compare the judge against people a few more times",
    Blocker.WEAK_DATASET: "collect more cases, and hold some back",
    Blocker.BUDGET_SPENT: "wait for reliability to recover, or ship this as a fix",
}


@dataclass(frozen=True)
class Signals:
    """What the evals say about a candidate release."""

    suite_may_gate: bool
    judge_may_gate: bool
    regressed: bool
    broken_cases: tuple[str, ...]
    error_budget_spent: bool
    is_fix: bool
    dataset_usable: bool

    def __post_init__(self) -> None:
        """Reject a regression that does not name what broke."""
        if self.regressed and not self.broken_cases:
            raise ValueError("a regression must name what broke")


@dataclass(frozen=True)
class Decision:
    """Whether to release, what is blocking, and what to do next."""

    release: bool
    blockers: tuple[Blocker, ...]
    exceptional: bool
    reason: str = ""
    next_step: str = ""


def decide_release(signals: Signals) -> Decision:
    """Decide whether `signals` clear the release gate."""
    found: set[Blocker] = set()

    if signals.regressed:
        found.add(Blocker.REGRESSED)
    if not signals.suite_may_gate:
        found.add(Blocker.UNRELIABLE_SUITE)
    if not signals.judge_may_gate:
        found.add(Blocker.UNPROVEN_JUDGE)
    if not signals.dataset_usable:
        found.add(Blocker.WEAK_DATASET)
    if signals.error_budget_spent and not signals.is_fix:
        found.add(Blocker.BUDGET_SPENT)

    blockers = tuple(blocker for blocker in ORDER if blocker in found)

    return Decision(
        release=not blockers,
        blockers=blockers,
        exceptional=signals.error_budget_spent and signals.is_fix and not blockers,
        reason=_reason(signals, blockers),
        next_step=NEXT_STEP[blockers[0]] if blockers else "",
    )


def _reason(signals: Signals, blockers: tuple[Blocker, ...]) -> str:
    """The sentence explaining the first blocker."""
    if not blockers:
        return ""
    if blockers[0] is Blocker.REGRESSED:
        return f"these cases stopped working: {', '.join(signals.broken_cases)}"
    return f"blocked by {blockers[0].value}"
