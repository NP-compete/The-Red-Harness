"""Turning check results into a decision about shipping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """One eval check's score, and whether it can block."""

    name: str
    score: float
    blocking: bool


@dataclass(frozen=True)
class Decision:
    """Whether the evals clear the gate, and what is in the way."""

    ok: bool
    blocked_by: tuple[str, ...] = ()
    regressions: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


def decide(
    *,
    results: list[CheckResult],
    baseline: dict[str, float],
    blocking: set[str] | None = None,
    tolerance: float = 0.01,
) -> Decision:
    """Decide whether `results` clear the gate against `baseline`."""
    if tolerance < 0:
        raise ValueError("a negative tolerance treats improvements as regressions")

    ran = {result.name: result for result in results}
    blocks = (
        blocking if blocking is not None else {r.name for r in results if r.blocking}
    )

    regressions = tuple(
        sorted(
            name
            for name, result in ran.items()
            if name in baseline and result.score < baseline[name] - tolerance
        )
    )

    missing = tuple(sorted(name for name in baseline if name not in ran))

    blocked_by = tuple(
        sorted(
            {
                *(n for n in regressions if n in blocks),
                *(n for n in missing if n in blocks),
            }
        )
    )

    return Decision(
        ok=not blocked_by,
        blocked_by=blocked_by,
        regressions=regressions,
        missing=missing,
    )
