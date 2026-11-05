"""Deciding what from a conversation is worth keeping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Decision(Enum):
    """Whether something said should be remembered."""

    KEEP = "keep"
    ASK = "ask"
    DISCARD = "discard"


@dataclass(frozen=True)
class Candidate:
    """Something said that might be worth remembering."""

    text: str
    durable: bool
    about_the_person: bool
    sensitive: bool
    already_known: bool
    stated_by_person: bool
    asked_to_remember: bool
    asked_to_forget: bool

    def __post_init__(self) -> None:
        """Reject a candidate with nothing in it."""
        if not self.text.strip():
            raise ValueError("there is nothing here to remember")


@dataclass(frozen=True)
class Captured:
    """Whether to remember something, and why."""

    decision: Decision
    text: str
    reason: str

    @property
    def needs_confirmation(self) -> bool:
        """Whether the person should be asked first."""
        return self.decision is Decision.ASK


def decide_capture(candidate: Candidate) -> Captured:
    """Decide whether `candidate` is worth remembering."""

    def outcome(decision: Decision, reason: str) -> Captured:
        """An outcome with this decision and reason."""
        return Captured(decision=decision, text=candidate.text, reason=reason)

    if candidate.asked_to_forget:
        return outcome(Decision.DISCARD, "the person asked for this not to be kept")

    if candidate.already_known:
        return outcome(Decision.DISCARD, "this is already remembered")

    if candidate.asked_to_remember:
        return outcome(Decision.KEEP, "the person asked for this to be kept")

    if candidate.sensitive:
        return outcome(
            Decision.ASK, "this is sensitive enough to be worth asking about"
        )

    if not candidate.stated_by_person:
        return outcome(Decision.ASK, "this was inferred rather than said")

    if not candidate.durable:
        return outcome(Decision.DISCARD, "this is only true for now")

    return outcome(Decision.KEEP, "")
