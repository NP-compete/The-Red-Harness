"""Breaking a compound question into the things actually being asked."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent.src.knowledge.coverage import Part

MAX_PARTS = 5

QUESTION_WORDS = (
    "what",
    "who",
    "when",
    "where",
    "why",
    "how",
    "which",
    "is",
    "are",
    "do",
    "does",
    "can",
    "should",
)

FILLER = {
    *QUESTION_WORDS,
    "the",
    "a",
    "an",
    "and",
    "also",
    "of",
    "to",
    "it",
    "its",
    "in",
    "on",
    "for",
    "about",
    "please",
    "thank",
    "you",
    "me",
    "my",
    "tell",
    "i",
}

_SPLIT = re.compile(r"\?|,\s*also\s+|\s+also\s+")
_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Split:
    """A question broken into its parts."""

    original: str
    parts: tuple[Part, ...]
    count: int
    compound: bool
    too_many: bool


def split_question(asked: str) -> Split:
    """Break `asked` into the separate questions it contains."""
    if not asked.strip():
        raise ValueError("there is no question to split")

    fragments: list[str] = []
    for piece in _SPLIT.split(asked):
        fragments.extend(_split_on_and(piece))

    parts = []
    for fragment in fragments:
        text = " ".join(fragment.split())
        keywords = tuple(
            word for word in _WORD.findall(text.lower()) if word not in FILLER
        )
        if text and keywords:
            parts.append(Part(question=text, keywords=keywords))

    if not parts:
        raise ValueError("there is nothing being asked here")

    return Split(
        original=asked,
        parts=tuple(parts),
        count=len(parts),
        compound=len(parts) > 1,
        too_many=len(parts) > MAX_PARTS,
    )


def _split_on_and(text: str) -> list[str]:
    """Split `text` on `and`, but only where a new question starts."""
    pieces = re.split(r"\s+and\s+", text)
    joined: list[str] = []
    for piece in pieces:
        first = piece.strip().split(" ")[0].lower() if piece.strip() else ""
        if joined and first not in QUESTION_WORDS:
            joined[-1] = f"{joined[-1]} and {piece.strip()}"
        else:
            joined.append(piece.strip())
    return [piece for piece in joined if piece]
