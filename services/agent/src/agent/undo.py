"""Putting back what a run changed, newest change first."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(Enum):
    """What happened when one change was undone."""

    UNDONE = "undone"
    ALREADY_GONE = "already-gone"
    FAILED = "failed"


@dataclass(frozen=True)
class Change:
    """One thing a run changed, and whether it can be put back."""

    target: str
    kind: str
    reversible: bool
    order: int

    def __post_init__(self) -> None:
        """Reject a change that does not say what it touched."""
        if not self.target.strip():
            raise ValueError("a change must say what it touched")


@dataclass(frozen=True)
class Plan:
    """The steps to undo a run, and what cannot be undone."""

    steps: tuple[Change, ...]
    cannot_undo: tuple[str, ...]
    complete: bool


@dataclass(frozen=True)
class Summary:
    """How an undo went, and what to tell the person."""

    all_undone: bool
    failed: tuple[str, ...]
    message: str
    warning: str = ""


def plan_undo(changes: list[Change]) -> Plan:
    """Work out how to undo `changes`, newest first."""
    if not changes:
        raise ValueError("there is nothing to undo")

    latest: dict[str, Change] = {}
    for item in changes:
        held = latest.get(item.target)
        if held is None or item.order > held.order:
            latest[item.target] = item

    cannot = tuple(
        sorted(item.target for item in latest.values() if not item.reversible)
    )

    return Plan(
        steps=tuple(
            sorted(
                (item for item in latest.values() if item.reversible),
                key=lambda item: item.order,
                reverse=True,
            )
        ),
        cannot_undo=cannot,
        complete=not cannot,
    )


def summarise_undo(results: dict[str, Outcome]) -> Summary:
    """Summarise the outcome of carrying out an undo plan."""
    if not results:
        raise ValueError("there is nothing to summarise")

    undone = [
        target for target, outcome in results.items() if outcome is Outcome.UNDONE
    ]
    gone = [
        target for target, outcome in results.items() if outcome is Outcome.ALREADY_GONE
    ]
    failed = tuple(
        sorted(
            target for target, outcome in results.items() if outcome is Outcome.FAILED
        )
    )

    parts = []
    if undone:
        parts.append(f"{len(undone)} undone")
    if gone:
        parts.append(f"{len(gone)} already gone")
    if failed:
        parts.append(f"{len(failed)} could not be undone")

    return Summary(
        all_undone=not failed,
        failed=failed,
        message=", ".join(parts),
        warning="this was partly undone, so things are not as they were"
        if failed
        else "",
    )
