"""Tracks text that came from an untrusted source, and where it ends up."""

from __future__ import annotations

from typing import Any


class TaintLedger:
    """Remembers untrusted text so writes derived from it can be spotted."""

    def __init__(self, min_length: int = 12) -> None:
        """Start empty, ignoring fragments shorter than `min_length`."""
        self._min_length = min_length
        self._fragments: list[str] = []
        self._origins: dict[str, set[str]] = {}

    def record(self, text: str, *, source: str = "") -> None:
        """Keep each line, and the whole, as separate fragments."""
        for piece in [text, *text.splitlines()]:
            cleaned = _normalise(piece)
            if len(cleaned) < self._min_length:
                continue
            if cleaned not in self._fragments:
                self._fragments.append(cleaned)
            if source:
                self._origins.setdefault(cleaned, set()).add(source)

    def every_source(self) -> tuple[str, ...]:
        """Everywhere this run has read from, named once each."""
        seen: set[str] = set()
        for origins in self._origins.values():
            seen |= origins
        return tuple(sorted(seen))

    def holds_anything(self) -> bool:
        """Whether anything was kept, for the coarse run-level rule."""
        return bool(self._fragments)

    def sources_for(self, text: str) -> tuple[str, ...]:
        """Which servers this text repeats something from."""
        haystack = _normalise(text)
        found: list[str] = []
        for fragment in self._fragments:
            if fragment not in haystack:
                continue
            for origin in sorted(self._origins.get(fragment, ())):
                if origin not in found:
                    found.append(origin)
        return tuple(found)

    def derives(self, args: dict[str, Any]) -> bool:
        """Whether any argument carries recorded untrusted text."""
        return bool(self.matched(args))

    def matched(self, args: dict[str, Any]) -> tuple[str, ...]:
        """The recorded fragments that appear in `args`."""
        haystacks = [_normalise(value) for value in _strings(args)]
        return tuple(
            fragment
            for fragment in self._fragments
            if any(fragment in haystack for haystack in haystacks)
        )


def _normalise(text: str) -> str:
    """`text` with its whitespace collapsed and lowercased."""
    return " ".join(text.split()).lower()


def _strings(value: Any) -> list[str]:
    """Every string reachable inside `value`."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, (list, tuple)):
        return [s for item in value for s in _strings(item)]
    return []
