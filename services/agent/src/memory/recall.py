"""Choosing which remembered things are worth bringing to this conversation."""

from __future__ import annotations

from dataclasses import dataclass

STATED = "stated"


@dataclass(frozen=True)
class Candidate:
    """One stored memory that might be worth recalling."""

    key: str
    keywords: tuple[str, ...]
    text: str
    scope: str
    source: str
    confidence: float
    pinned: bool
    words: int

    def __post_init__(self) -> None:
        """Reject a memory with no keywords or nothing in it."""
        if not self.keywords:
            raise ValueError("a memory must say what it is about")
        if self.words < 1:
            raise ValueError("a memory must have something in it")


@dataclass(frozen=True)
class Recalled:
    """One memory actually recalled, and why."""

    key: str
    text: str
    because: str


@dataclass(frozen=True)
class Recall:
    """What was recalled, what was left out, and how many words it came to."""

    recalled: tuple[Recalled, ...]
    left_out: tuple[str, ...]
    words: int


def recall(
    candidates: list[Candidate], *, about: tuple[str, ...], budget_words: int
) -> Recall:
    """Pick the memories worth recalling about `about`, within the budget."""
    if budget_words < 1:
        raise ValueError("there must be room for something")
    if not about:
        raise ValueError("there is no subject to recall against")

    eligible = [
        (candidate, reason)
        for candidate in candidates
        if (reason := _reason(candidate, about)) is not None
    ]

    eligible.sort(
        key=lambda pair: (
            not pair[0].pinned,
            pair[0].source != STATED,
            -pair[0].confidence,
            pair[0].key,
        )
    )

    recalled: list[Recalled] = []
    left_out: list[str] = []
    used = 0

    for candidate, reason in eligible:
        if used + candidate.words <= budget_words:
            recalled.append(
                Recalled(key=candidate.key, text=candidate.text, because=reason)
            )
            used += candidate.words
        else:
            left_out.append(candidate.key)

    return Recall(recalled=tuple(recalled), left_out=tuple(left_out), words=used)


def _reason(candidate: Candidate, about: tuple[str, ...]) -> str | None:
    """Why `candidate` is relevant, or `None` if it is not."""
    if candidate.pinned:
        return "pinned"
    for topic in about:
        if topic in candidate.keywords:
            return topic
    return None
