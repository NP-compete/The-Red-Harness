"""Collapsing passages that say the same thing twice."""

from __future__ import annotations

import re
from dataclasses import dataclass

SAME_ENOUGH = 0.6
AUTHORITY_RANK = {"policy": 3, "reference": 2, "note": 1}

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "for",
    "by",
}
_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Passage:
    """One retrieved passage, its score and how authoritative it is."""

    source: str
    text: str
    score: float
    authority: str = "reference"

    def __post_init__(self) -> None:
        """Reject an empty passage or a score outside zero to one."""
        if not self.text.strip():
            raise ValueError("a passage must say something")
        if not 0 <= self.score <= 1:
            raise ValueError("a score runs from nothing to certainty")


@dataclass(frozen=True)
class Kept:
    """One passage kept after collapsing, and what it stood in for."""

    source: str
    text: str
    score: float
    authority: str
    also_in: tuple[str, ...]
    corroborated: bool


@dataclass(frozen=True)
class Collapsed:
    """The passages kept, and how many were folded into them."""

    kept: tuple[Kept, ...]
    collapsed: int


def collapse(passages: list[Passage]) -> Collapsed:
    """Fold near-duplicate passages into the most authoritative of each."""
    if not passages:
        raise ValueError("there is nothing to collapse")

    groups: list[list[Passage]] = []
    for passage in passages:
        words = _words(passage.text)
        for group in groups:
            if _overlap(words, _words(group[0].text)) >= SAME_ENOUGH:
                group.append(passage)
                break
        else:
            groups.append([passage])

    kept = [
        Kept(
            source=(best := _best(group)).source,
            text=best.text,
            score=best.score,
            authority=best.authority,
            also_in=tuple(sorted(p.source for p in group if p.source != best.source)),
            corroborated=len(group) > 1,
        )
        for group in groups
    ]

    kept.sort(key=lambda item: (-item.score, item.source))

    return Collapsed(kept=tuple(kept), collapsed=len(passages) - len(kept))


def _best(group: list[Passage]) -> Passage:
    """The most authoritative, highest-scoring passage of a group."""
    return max(group, key=lambda p: (AUTHORITY_RANK.get(p.authority, 0), p.score))


def _words(text: str) -> set[str]:
    """The meaningful words of `text`, lowercased."""
    return {word for word in _WORD.findall(text.lower()) if word not in STOPWORDS}


def _overlap(left: set[str], right: set[str]) -> float:
    """How far two word sets overlap, from nothing to one."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
