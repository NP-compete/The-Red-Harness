"""Giving a retrieved passage enough of its surroundings to make sense."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """One chunk of a document, and where it sits in it."""

    document: str
    index: int
    text: str
    words: int

    def __post_init__(self) -> None:
        """Reject a chunk with no words in it."""
        if self.words < 1:
            raise ValueError("a passage must have some words in it")


@dataclass(frozen=True)
class Neighbourhood:
    """A matched chunk with its neighbours, within a word budget."""

    chunks: tuple[Chunk, ...]
    matched_index: int
    text: str
    words: int
    trimmed: bool


def expand(
    match: Chunk, *, within: tuple[Chunk, ...], budget_words: int
) -> Neighbourhood:
    """Widen `match` to its neighbours, up to `budget_words`."""
    if budget_words < 1:
        raise ValueError("there must be room for something")
    if not within:
        raise ValueError("there is nothing to expand within")
    if not any(c.document == match.document and c.index == match.index for c in within):
        raise ValueError("that passage is not in this collection")

    siblings = {
        chunk.index: chunk for chunk in within if chunk.document == match.document
    }
    before = siblings.get(match.index - 1)
    after = siblings.get(match.index + 1)

    kept = [match]
    used = match.words

    for neighbour in (before, after):
        if neighbour is None:
            continue
        if used + neighbour.words <= budget_words:
            kept.append(neighbour)
            used += neighbour.words

    kept.sort(key=lambda chunk: chunk.index)
    available = len([n for n in (before, after) if n is not None])

    return Neighbourhood(
        chunks=tuple(kept),
        matched_index=match.index,
        text=" ".join(chunk.text for chunk in kept),
        words=used,
        trimmed=len(kept) - 1 < available,
    )
