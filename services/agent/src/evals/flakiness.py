"""Finding cases that do not give the same answer twice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MIN_ATTEMPTS = 3


class Stability(Enum):
    """Whether a case gives the same answer each time."""

    STEADY = "steady"
    FLAKY = "flaky"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Attempt:
    """One run of one eval case."""

    case_id: str
    run: int
    passed: bool


@dataclass(frozen=True)
class CaseResult:
    """How one case fared across its attempts."""

    stability: Stability
    passes: bool
    pass_rate: float
    attempts: int
    reason: str = ""


@dataclass(frozen=True)
class Flakiness:
    """How flaky a suite is, and whether it may gate a release."""

    cases: dict[str, CaseResult]
    flaky: tuple[str, ...]
    flaky_share: float
    worst: str
    may_gate: bool


def assess_flakiness(attempts: list[Attempt]) -> Flakiness:
    """Assess how steady each case is across `attempts`."""
    if not attempts:
        raise ValueError("there is nothing to assess")

    keys = [(attempt.case_id, attempt.run) for attempt in attempts]
    if len(keys) != len(set(keys)):
        raise ValueError("the same run cannot be counted twice")

    grouped: dict[str, list[Attempt]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.case_id, []).append(attempt)

    cases = {case_id: _assess(group) for case_id, group in grouped.items()}
    flaky = tuple(
        sorted(
            case
            for case, result in cases.items()
            if result.stability is Stability.FLAKY
        )
    )
    unknown = any(result.stability is Stability.UNKNOWN for result in cases.values())

    return Flakiness(
        cases=cases,
        flaky=flaky,
        flaky_share=len(flaky) / len(cases),
        worst=min(flaky, key=lambda case: abs(cases[case].pass_rate - 0.5))
        if flaky
        else "",
        may_gate=not flaky and not unknown,
    )


def _assess(group: list[Attempt]) -> CaseResult:
    """Assess one case's attempts."""
    passed = sum(1 for attempt in group if attempt.passed)
    rate = passed / len(group)

    if len(group) < MIN_ATTEMPTS:
        return CaseResult(
            stability=Stability.UNKNOWN,
            passes=rate == 1.0,
            pass_rate=rate,
            attempts=len(group),
            reason=f"{MIN_ATTEMPTS} attempts are needed before judging this",
        )

    steady = rate in (0.0, 1.0)

    return CaseResult(
        stability=Stability.STEADY if steady else Stability.FLAKY,
        passes=rate == 1.0,
        pass_rate=rate,
        attempts=len(group),
        reason="" if steady else f"passed {passed} of {len(group)} times",
    )
