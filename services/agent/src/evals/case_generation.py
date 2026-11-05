"""Turning a filed complaint into a case the suite can run."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Complaint:
    """Someone's report that an answer was wrong."""

    run: str
    question: str
    answer_given: str
    what_was_wrong: str
    expected: str
    reproducible: bool
    content_kept: bool
    contains_personal_data: bool

    def __post_init__(self) -> None:
        """Reject a complaint that is about no question."""
        if not self.question.strip():
            raise ValueError("a complaint must be about a question")


@dataclass(frozen=True)
class Existing:
    """One eval case already in the suite."""

    case: str
    question: str


@dataclass(frozen=True)
class Proposal:
    """Whether a complaint should become a case, and why not."""

    proposed: bool
    question: str
    expected: str
    from_run: str
    needs_review: bool
    reason: str = ""
    duplicate_of: str = ""


def _same(one: str, other: str) -> bool:
    """Whether two questions are the same once whitespace and case are ignored."""
    return _SPACE.sub(" ", one.strip().lower()) == _SPACE.sub(
        " ", other.strip().lower()
    )


def propose_case(complaint: Complaint, *, existing: list[Existing]) -> Proposal:
    """Decide whether `complaint` should become a new eval case."""

    def no(reason: str, duplicate_of: str = "") -> Proposal:
        """A refusal with this reason."""
        return Proposal(
            proposed=False,
            question=complaint.question,
            expected=complaint.expected,
            from_run=complaint.run,
            needs_review=False,
            reason=reason,
            duplicate_of=duplicate_of,
        )

    if not complaint.content_kept:
        return no("the conversation was not kept, so there is nothing to replay")
    if not complaint.expected.strip():
        return no("without an expected answer there is nothing to grade against")
    if not complaint.reproducible:
        return no("this could not be reproduced")

    match = next((e for e in existing if _same(e.question, complaint.question)), None)
    if match is not None:
        return no("the suite already asks this", duplicate_of=match.case)

    return Proposal(
        proposed=True,
        question=complaint.question,
        expected=complaint.expected,
        from_run=complaint.run,
        needs_review=complaint.contains_personal_data,
    )
