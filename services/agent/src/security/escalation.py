"""Who to ask next when a run is waiting on a person."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Step:
    """One rung of an escalation ladder: who to ask, and for how long."""

    contact: str
    wait: timedelta

    def __post_init__(self) -> None:
        """Reject a step naming nobody or allowing no time to answer."""
        if not self.contact.strip():
            raise ValueError("a step must name someone to ask")
        if self.wait <= timedelta(0):
            raise ValueError("a step must allow some time to answer")


@dataclass(frozen=True)
class Ladder:
    """Who to ask in turn, and when to give up."""

    steps: tuple[Step, ...]
    give_up_after: timedelta

    def __post_init__(self) -> None:
        """Reject an empty ladder, or one giving up before its first wait."""
        if not self.steps:
            raise ValueError("a ladder must have someone on it")
        if self.give_up_after < self.steps[0].wait:
            raise ValueError("a ladder cannot give up before its first wait is over")


@dataclass(frozen=True)
class Escalation:
    """Who to ask next, and whether the ladder has run out."""

    contact: str
    step_index: int
    waiting: bool = False
    repeated: bool = False
    gave_up: bool = False
    approved: bool = False
    next_at: datetime | None = None
    reason: str = ""


def escalate(
    ladder: Ladder,
    *,
    asked_at: datetime | None,
    now: datetime,
    step_index: int = 0,
    started_at: datetime | None = None,
) -> Escalation:
    """Work out who to ask next, given who was asked and when."""
    if asked_at is None:
        return Escalation(contact=ladder.steps[0].contact, step_index=0)

    due_at = asked_at + ladder.steps[step_index].wait
    if now < due_at:
        return Escalation(
            contact="", step_index=step_index, waiting=True, next_at=due_at
        )

    if started_at is not None and now - started_at > ladder.give_up_after:
        hours = (now - started_at).total_seconds() / 3600
        return Escalation(
            contact="",
            step_index=step_index,
            gave_up=True,
            approved=False,
            reason=f"nobody answered in {hours:.0f} hours",
        )

    last = len(ladder.steps) - 1
    nxt = min(step_index + 1, last)
    return Escalation(
        contact=ladder.steps[nxt].contact,
        step_index=nxt,
        repeated=nxt == step_index,
    )
