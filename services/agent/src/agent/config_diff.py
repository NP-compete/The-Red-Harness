"""Describing what changed between two sets of settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Change(Enum):
    """How one config key differs."""

    CHANGED = "changed"
    ADDED = "added"
    REMOVED = "removed"


@dataclass(frozen=True)
class Entry:
    """One changed config key, before and after."""

    key: str
    kind: Change
    before: str
    after: str
    loosens: bool


@dataclass(frozen=True)
class Diff:
    """Every config change, and whether any of them loosens a limit."""

    changes: tuple[Entry, ...]
    count: int
    loosens: bool
    summary: str


def diff_config(before: dict[str, str], after: dict[str, str]) -> Diff:
    """Compare two config mappings."""
    if not before and not after:
        raise ValueError("there is nothing to compare")

    entries: list[Entry] = []

    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old == new:
            continue
        if old is None:
            entries.append(Entry(key, Change.ADDED, "", new or "", loosens=False))
        elif new is None:
            entries.append(Entry(key, Change.REMOVED, old, "", loosens=True))
        else:
            entries.append(
                Entry(key, Change.CHANGED, old, new, loosens=_raises(old, new))
            )

    counts = {kind: sum(1 for e in entries if e.kind is kind) for kind in Change}

    return Diff(
        changes=tuple(entries),
        count=len(entries),
        loosens=any(entry.loosens for entry in entries),
        summary=_summarise(counts),
    )


def _raises(before: str, after: str) -> bool:
    """Whether `after` is a larger number than `before`."""
    try:
        return float(after) > float(before)
    except ValueError:
        return False


def _summarise(counts: dict[Change, int]) -> str:
    """The one-line summary of a diff."""
    parts = [
        f"{counts[kind]} {kind.value}"
        for kind in (Change.CHANGED, Change.ADDED, Change.REMOVED)
        if counts[kind]
    ]
    return ", ".join(parts) if parts else "nothing changed"
