"""Noticing when sources give different answers to the same question."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

AUTHORITY_RANK = {"policy": 3, "reference": 2, "note": 1}
CLEARLY_NEWER = timedelta(days=90)


class Stance(Enum):
    """Whether two sources say the same thing."""

    AGREED = "agreed"
    DISAGREED = "disagreed"


@dataclass(frozen=True)
class Finding:
    """What one source says, and how authoritative it is."""

    source: str
    answer: str
    updated_at: datetime
    authority: str = "reference"

    def __post_init__(self) -> None:
        """Reject a finding with no source or nothing to say."""
        if not self.source.strip():
            raise ValueError("a finding must say where it came from")
        if not self.answer.strip():
            raise ValueError("a finding must say something")


@dataclass(frozen=True)
class Disagreement:
    """Whether the sources agree, and which answer to prefer."""

    stance: Stance
    disagree: bool
    answers: tuple[str, ...]
    by_answer: dict[str, tuple[str, ...]]
    preferred: str
    show_both: bool
    reason: str = ""


def find_disagreement(findings: list[Finding], *, now: datetime) -> Disagreement:
    """Compare what the sources say as of `now`."""
    if not findings:
        raise ValueError("there is nothing to compare")

    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.answer.strip().lower(), []).append(finding)

    answers = tuple(sorted(grouped))
    by_answer = {
        answer: tuple(sorted(f.source for f in group))
        for answer, group in grouped.items()
    }

    if len(grouped) == 1:
        return Disagreement(
            stance=Stance.AGREED,
            disagree=False,
            answers=answers,
            by_answer=by_answer,
            preferred=answers[0],
            show_both=False,
        )

    preferred, reason = _prefer(grouped, now=now)

    return Disagreement(
        stance=Stance.DISAGREED,
        disagree=True,
        answers=answers,
        by_answer=by_answer,
        preferred=preferred,
        show_both=True,
        reason=reason,
    )


def _prefer(grouped: dict[str, list[Finding]], *, now: datetime) -> tuple[str, str]:
    """The answer to prefer, and why it wins."""
    best_authority = {
        answer: max(AUTHORITY_RANK.get(f.authority, 0) for f in group)
        for answer, group in grouped.items()
    }
    top = max(best_authority.values())
    leaders = [answer for answer, rank in best_authority.items() if rank == top]

    if len(leaders) == 1:
        winner = leaders[0]
        kind = max(
            grouped[winner], key=lambda f: AUTHORITY_RANK.get(f.authority, 0)
        ).authority
        return winner, f"this comes from a {kind}, which outranks the others"

    newest = {
        answer: max(f.updated_at for f in group) for answer, group in grouped.items()
    }
    ordered = sorted(newest.items(), key=lambda item: item[1], reverse=True)
    if ordered[0][1] - ordered[1][1] >= CLEARLY_NEWER:
        return ordered[0][0], "this source was updated much more recently"

    return "", "the sources disagree and nothing marks one as better"
