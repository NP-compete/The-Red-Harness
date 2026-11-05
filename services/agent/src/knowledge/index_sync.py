"""Whether what is indexed still matches what exists."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class State(Enum):
    """How well the index matches its source."""

    IN_STEP = "in-step"
    BEHIND = "behind"
    NEEDS_TIDYING = "needs-tidying"
    BROKEN = "broken"


@dataclass(frozen=True)
class Snapshot:
    """What the source holds, what is indexed, and what failed."""

    in_source: tuple[str, ...]
    indexed: tuple[str, ...]
    failed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject a document both indexed and failed."""
        both = set(self.indexed) & set(self.failed)
        if both:
            raise ValueError(f"indexed and failed at once: {', '.join(sorted(both))}")


@dataclass(frozen=True)
class Comparison:
    """How far the index has drifted from its source."""

    state: State
    missing: tuple[str, ...]
    orphaned: tuple[str, ...]
    failed: tuple[str, ...]
    coverage: float
    trustworthy: bool


def compare_index(snapshot: Snapshot) -> Comparison:
    """Compare what is indexed against what the source holds."""
    source = set(snapshot.in_source)
    indexed = set(snapshot.indexed)
    failed = set(snapshot.failed)

    missing = tuple(sorted(source - indexed - failed))
    orphaned = tuple(sorted(indexed - source))

    if failed:
        state = State.BROKEN
    elif missing:
        state = State.BEHIND
    elif orphaned:
        state = State.NEEDS_TIDYING
    else:
        state = State.IN_STEP

    return Comparison(
        state=state,
        missing=missing,
        orphaned=orphaned,
        failed=tuple(sorted(failed)),
        coverage=len(source & indexed) / len(source) if source else 1.0,
        trustworthy=not missing and not failed,
    )
