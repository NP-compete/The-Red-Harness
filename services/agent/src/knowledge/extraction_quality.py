"""Reading a document, and being honest about how well it was read."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Reader:
    """One document reader and whether it reports its own confidence."""

    name: str
    reports_confidence: bool


@dataclass(frozen=True)
class Attempt:
    """What one reader got out of a document, and how sure it is."""

    text: str
    confidence: float


@dataclass(frozen=True)
class Extraction:
    """The text finally taken from a document, and how it was got."""

    text: str
    confidence: float
    reader: str
    degraded: bool
    tried: tuple[str, ...]
    note: str = ""


def register(reader: Reader) -> Reader:
    """Accept a reader, rejecting one that cannot report its confidence."""
    if not reader.reports_confidence:
        raise ValueError(f"reader '{reader.name}' cannot report its confidence")
    return reader


class ReaderChain:
    """Readers tried in order until one clears the quality floor."""

    def __init__(self, readers: list[Reader], quality_floor: float) -> None:
        """Bind the chain to `readers` and the confidence floor to clear."""
        self._readers = [register(r) for r in readers]
        self._floor = quality_floor

    def read(self, attempt: Callable[[Reader], Attempt]) -> Extraction:
        """Try each reader in turn and return the best extraction."""
        tried: list[str] = []
        best: tuple[Reader, Attempt] | None = None

        for reader in self._readers:
            try:
                result = attempt(reader)
            except Exception:
                continue
            tried.append(reader.name)

            if best is None or result.confidence > best[1].confidence:
                best = (reader, result)
            if result.confidence >= self._floor:
                break

        if best is None:
            raise RuntimeError("no reader could read this document")

        reader, result = best
        degraded = result.confidence < self._floor
        return Extraction(
            text=result.text,
            confidence=result.confidence,
            reader=reader.name,
            degraded=degraded,
            tried=tuple(tried),
            note=(
                f"Read with low confidence ({result.confidence:.0%}); some content may be wrong."
                if degraded
                else ""
            ),
        )
