"""Working out which retrieved sources an answer actually used."""

from __future__ import annotations

from dataclasses import dataclass

_MIN_OVERLAP = 12


@dataclass(frozen=True)
class Chunk:
    """One retrieved chunk and how well it scored."""

    chunk_id: str
    document: str
    text: str
    score: float


@dataclass(frozen=True)
class Attribution:
    """Which chunks the answer actually drew on."""

    used: tuple[Chunk, ...]
    retrieved_but_unused: tuple[Chunk, ...]
    documents: tuple[str, ...]
    grounded: bool


def attribute(*, answer: str, chunks: list[Chunk]) -> Attribution:
    """Work out which of `chunks` the answer borrowed from."""
    needle = _normalise(answer)

    used: list[Chunk] = []
    unused: list[Chunk] = []
    for chunk in chunks:
        if _borrowed(needle, _normalise(chunk.text)):
            used.append(chunk)
        else:
            unused.append(chunk)

    used.sort(key=lambda c: needle.find(_longest_shared(needle, _normalise(c.text))))

    documents: list[str] = []
    for chunk in used:
        if chunk.document not in documents:
            documents.append(chunk.document)

    return Attribution(
        used=tuple(used),
        retrieved_but_unused=tuple(unused),
        documents=tuple(documents),
        grounded=bool(used),
    )


def _normalise(text: str) -> str:
    """`text` with its whitespace collapsed and lowercased."""
    return " ".join(text.split()).lower()


def _borrowed(answer: str, source: str) -> bool:
    """Whether the answer shares enough text with the source to count."""
    return len(_longest_shared(answer, source)) >= _MIN_OVERLAP


def _longest_shared(answer: str, source: str) -> str:
    """The longest run of `source` that appears in `answer`."""
    best = ""
    for start in range(len(source)):
        for end in range(len(source), start + len(best), -1):
            fragment = source[start:end]
            if fragment in answer:
                best = fragment
                break
    return best
