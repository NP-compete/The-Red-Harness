"""Turning what someone asked into what to search for."""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Glossary:
    """The terms to expand and the words to drop."""

    expansions: dict[str, tuple[str, ...]]
    stopwords: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a term with nothing to expand into."""
        empty = [term for term, values in self.expansions.items() if not values]
        if empty:
            raise ValueError(f"nothing to expand {', '.join(sorted(empty))} into")


@dataclass(frozen=True)
class Rewritten:
    """The rewritten query, and what was expanded or removed."""

    original: str
    query: str
    expanded: tuple[str, ...]
    removed: tuple[str, ...]
    too_vague: bool


def rewrite_query(asked: str, *, glossary: Glossary) -> Rewritten:
    """Rewrite `asked` using `glossary`."""
    if not asked.strip():
        raise ValueError("there is no question to rewrite")

    words = list(dict.fromkeys(_WORD.findall(asked.lower())))
    stopwords = set(glossary.stopwords)

    kept = [word for word in words if word not in stopwords]
    removed = tuple(word for word in words if word in stopwords)

    too_vague = not kept
    if too_vague:
        kept = words

    expanded = tuple(word for word in kept if word in glossary.expansions)
    phrases = [phrase for word in expanded for phrase in glossary.expansions[word]]

    return Rewritten(
        original=asked,
        query=" ".join(dict.fromkeys([*kept, *phrases])),
        expanded=expanded,
        removed=removed,
        too_vague=too_vague,
    )
