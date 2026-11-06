"""Comparing how two versions did on the same set of cases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(Enum):
    """Whether a change helped, hurt, or neither."""

    IMPROVED = "improved"
    REGRESSED = "regressed"
    NO_CHANGE = "no-change"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Case:
    """One eval case, before and after a change."""

    case_id: str
    before: bool
    after: bool


@dataclass(frozen=True)
class Comparison:
    """What broke, what was fixed, and the verdict overall."""

    verdict: Verdict
    broken: tuple[str, ...]
    fixed: tuple[str, ...]
    before_rate: float
    after_rate: float
    summary: str
    reason: str = ""


def compare_runs(cases: list[Case], *, min_cases: int = 1) -> Comparison:
    """Compare `cases` before and after a change."""
    if not cases:
        raise ValueError("there is nothing to compare")

    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("a case cannot appear twice in one comparison")

    broken = tuple(sorted(c.case_id for c in cases if c.before and not c.after))
    fixed = tuple(sorted(c.case_id for c in cases if not c.before and c.after))

    before_rate = sum(c.before for c in cases) / len(cases)
    after_rate = sum(c.after for c in cases) / len(cases)

    summary = (
        "nothing changed"
        if not broken and not fixed
        else ", ".join(
            part
            for part in (
                f"{len(broken)} broke" if broken else "",
                f"{len(fixed)} fixed" if fixed else "",
            )
            if part
        )
    )

    if broken:
        verdict, reason = Verdict.REGRESSED, ""
    elif len(cases) < min_cases:
        verdict = Verdict.INCONCLUSIVE
        reason = f"{min_cases} cases are needed before calling this an improvement"
    elif fixed:
        verdict, reason = Verdict.IMPROVED, ""
    else:
        verdict, reason = Verdict.NO_CHANGE, ""

    return Comparison(
        verdict=verdict,
        broken=broken,
        fixed=fixed,
        before_rate=before_rate,
        after_rate=after_rate,
        summary=summary,
        reason=reason,
    )
