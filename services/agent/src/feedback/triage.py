"""Turning a rating into something that can be acted on."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(Enum):
    """What to do with a piece of feedback."""

    THANK = "thank"
    ASK_WHY = "ask_why"
    FILE = "file"
    ROUTE_TO_POLICY = "route_to_policy"


@dataclass(frozen=True)
class Rating:
    """One thumbs up or down, and the run it was about."""

    run: str
    liked: bool
    comment: str
    answer_had_sources: bool
    answer_was_refused: bool
    run_failed: bool
    may_keep_content: bool

    def __post_init__(self) -> None:
        """Reject a rating that does not say what it is about."""
        if not self.run.strip():
            raise ValueError("a rating must say what it is about")


@dataclass(frozen=True)
class Triaged:
    """What to do with a rating, and what may be kept with it."""

    run: str
    action: Action
    comment: str
    asked_for_detail: bool
    attach_content: bool
    becomes_eval_case: bool


def triage(rating: Rating) -> Triaged:
    """Decide what to do with `rating`."""
    attach_content = rating.may_keep_content

    if rating.liked:
        return Triaged(
            run=rating.run,
            action=Action.THANK,
            comment=rating.comment,
            asked_for_detail=False,
            attach_content=attach_content,
            becomes_eval_case=False,
        )

    if rating.answer_was_refused:
        action = Action.ROUTE_TO_POLICY
    elif rating.run_failed or rating.comment.strip():
        action = Action.FILE
    else:
        action = Action.ASK_WHY

    return Triaged(
        run=rating.run,
        action=action,
        comment=rating.comment,
        asked_for_detail=action is Action.ASK_WHY,
        attach_content=attach_content,
        becomes_eval_case=attach_content and action is Action.FILE,
    )
