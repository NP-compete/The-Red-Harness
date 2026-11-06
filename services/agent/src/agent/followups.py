"""Offering next questions that this agent could actually answer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    """One follow-up that could be offered, and what it needs."""

    text: str
    needs: tuple[str, ...]
    about: str

    def __post_init__(self) -> None:
        """Reject a suggestion that says nothing."""
        if not self.text.strip():
            raise ValueError("a suggestion must say something")


@dataclass(frozen=True)
class Context:
    """What the answer covered and what the agent can still do."""

    available_tools: tuple[str, ...]
    topics_covered: tuple[str, ...]
    already_asked: tuple[str, ...]
    answer_was_complete: bool
    limit: int

    def __post_init__(self) -> None:
        """Reject a context with no room for a suggestion."""
        if self.limit < 1:
            raise ValueError("there must be room for at least one suggestion")


@dataclass(frozen=True)
class Offered:
    """One follow-up actually offered, and why."""

    text: str
    because: str


@dataclass(frozen=True)
class Followups:
    """The follow-ups offered, and how many were set aside."""

    offered: tuple[Offered, ...]
    set_aside: int
    reason: str = ""


def choose_followups(candidates: list[Candidate], *, context: Context) -> Followups:
    """Pick which follow-ups to offer, given what the answer covered."""
    if not context.answer_was_complete:
        return Followups(
            offered=(),
            set_aside=len(candidates),
            reason="part of the question is still unanswered",
        )

    tools = set(context.available_tools)
    covered = set(context.topics_covered)
    asked = set(context.already_asked)

    usable: list[Offered] = []
    seen: set[str] = set()
    set_aside = 0

    for candidate in candidates:
        possible = set(candidate.needs) <= tools
        on_topic = candidate.about in covered
        fresh = candidate.text not in asked and candidate.text not in seen

        if not (possible and on_topic and fresh):
            if candidate.text not in seen:
                set_aside += 1
            continue

        seen.add(candidate.text)
        usable.append(Offered(text=candidate.text, because=candidate.about))

    return Followups(offered=tuple(usable[: context.limit]), set_aside=set_aside)
