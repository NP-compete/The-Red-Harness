"""Whether what was found covers every part of what was asked."""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Part:
    """One part of a question, and the words that would answer it."""

    question: str
    keywords: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a part that does not say what to look for."""
        if not self.keywords:
            raise ValueError("a part must say what to look for")


@dataclass(frozen=True)
class Coverage:
    """Which parts the retrieved passages cover, and which they miss."""

    complete: bool
    covered_by: dict[str, tuple[int, ...]]
    uncovered: tuple[str, ...]
    unused: tuple[int, ...]
    share: float
    reason: str = ""


def check_coverage(parts: tuple[Part, ...], *, found: tuple[str, ...]) -> Coverage:
    """Check which of `parts` the `found` passages actually cover."""
    if not parts:
        raise ValueError("there is nothing to check coverage of")

    words = [set(_WORD.findall(passage.lower())) for passage in found]

    covered_by = {
        part.question: tuple(
            index for index, passage in enumerate(words) if _mentions(passage, part)
        )
        for part in parts
    }

    uncovered = tuple(question for question, hits in covered_by.items() if not hits)
    used = {index for hits in covered_by.values() for index in hits}
    share = (len(parts) - len(uncovered)) / len(parts)

    if share == 0:
        reason = "nothing was found for any part of this"
    elif uncovered:
        reason = f"nothing found for: {', '.join(uncovered)}"
    else:
        reason = ""

    return Coverage(
        complete=not uncovered,
        covered_by=covered_by,
        uncovered=uncovered,
        unused=tuple(index for index in range(len(found)) if index not in used),
        share=share,
        reason=reason,
    )


def _mentions(passage: set[str], part: Part) -> bool:
    """Whether a passage mentions anything `part` is looking for."""
    return any(
        word.startswith(keyword) for keyword in part.keywords for word in passage
    )
