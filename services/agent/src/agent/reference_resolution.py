"""Working out what a follow-up question is pointing at."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REACH = 5

_WORD = re.compile(r"[A-Za-z0-9_-]+")
_POINTERS = {"it", "its", "that", "this", "them", "they", "those", "these", "one"}


@dataclass(frozen=True)
class Mention:
    """One entity mentioned earlier, and how far back."""

    entity: str
    kind: str
    turns_ago: int
    was_the_subject: bool

    def __post_init__(self) -> None:
        """Reject a mention from the future."""
        if self.turns_ago < 0:
            raise ValueError("a mention cannot come from the future")


@dataclass(frozen=True)
class Resolved:
    """What a reference points at, or the candidates to ask about."""

    entity: str | None
    resolved: bool
    should_ask: bool
    candidates: list[str] = field(default_factory=list)


def resolve_reference(question: str, *, mentions: list[Mention]) -> Resolved:
    """Work out what `question` refers to, given what was mentioned."""
    if not question.strip():
        raise ValueError("there is no question to resolve")

    words = [word.lower() for word in _WORD.findall(question)]

    if any(mention.entity.lower() in words for mention in mentions):
        return Resolved(entity=None, resolved=False, should_ask=False)

    if not _POINTERS & set(words):
        return Resolved(entity=None, resolved=False, should_ask=False)

    kinds = {mention.kind.lower() for mention in mentions}
    hinted = next((word for word in words if word in kinds), None)

    reachable = [
        mention
        for mention in mentions
        if mention.turns_ago <= REACH
        and (hinted is None or mention.kind.lower() == hinted)
    ]
    if not reachable:
        return Resolved(entity=None, resolved=False, should_ask=True)

    ranked = sorted(reachable, key=lambda m: (not m.was_the_subject, m.turns_ago))
    best = ranked[0]
    tied = [
        mention
        for mention in ranked
        if (mention.was_the_subject, mention.turns_ago)
        == (best.was_the_subject, best.turns_ago)
    ]

    if len(tied) > 1:
        return Resolved(
            entity=None,
            resolved=False,
            should_ask=True,
            candidates=[mention.entity for mention in tied],
        )

    return Resolved(entity=best.entity, resolved=True, should_ask=False)
