"""Scoring an answer against a rubric, and saying when the score is not trustworthy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    """One thing a rubric asks about, and what it counts for."""

    name: str
    weight: float
    required: bool

    def __post_init__(self) -> None:
        """Reject a criterion with no name or no weight."""
        if not self.name.strip():
            raise ValueError("a criterion must have a name")
        if self.weight <= 0:
            raise ValueError("a criterion that counts for nothing is not a criterion")


@dataclass(frozen=True)
class Rubric:
    """What an answer is judged on, and the mark it must clear."""

    criteria: tuple[Criterion, ...]
    pass_mark: float

    def __post_init__(self) -> None:
        """Reject an empty rubric or a pass mark outside zero to one."""
        if not self.criteria:
            raise ValueError("a rubric must ask something")
        if not 0 <= self.pass_mark <= 1:
            raise ValueError("a pass mark runs from nothing to everything")


@dataclass(frozen=True)
class Judgement:
    """An answer's score against a rubric, and what it met."""

    score: float
    passed: bool
    reliable: bool
    met: tuple[str, ...]
    unmet: tuple[str, ...]
    unanswered: tuple[str, ...]
    reason: str = ""


def score_answer(answers: dict[str, bool], *, rubric: Rubric) -> Judgement:
    """Score `answers` against `rubric`."""
    names = {criterion.name for criterion in rubric.criteria}
    unknown = set(answers) - names
    if unknown:
        raise ValueError(f"the rubric does not ask about {', '.join(sorted(unknown))}")

    met = tuple(c.name for c in rubric.criteria if answers.get(c.name) is True)
    unmet = tuple(c.name for c in rubric.criteria if answers.get(c.name) is False)
    unanswered = tuple(c.name for c in rubric.criteria if c.name not in answers)

    total = sum(c.weight for c in rubric.criteria)
    earned = sum(c.weight for c in rubric.criteria if c.name in met)
    score = earned / total

    missing_required = [
        c.name for c in rubric.criteria if c.required and c.name not in met
    ]
    reliable = not unanswered

    if missing_required:
        reason = f"did not meet {', '.join(missing_required)}"
    elif not reliable:
        reason = f"nothing was said about {', '.join(unanswered)}"
    else:
        reason = ""

    return Judgement(
        score=score,
        passed=reliable and not missing_required and score >= rubric.pass_mark,
        reliable=reliable,
        met=met,
        unmet=unmet,
        unanswered=unanswered,
        reason=reason,
    )
