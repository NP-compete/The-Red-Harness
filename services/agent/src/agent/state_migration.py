"""Bringing stored conversation state up to the version in use."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(Enum):
    """What happened when stored state was brought up to date."""

    ALREADY_CURRENT = "already-current"
    MIGRATED = "migrated"
    TOO_NEW = "too-new"
    NO_PATH = "no-path"


@dataclass(frozen=True)
class Step:
    """One migration step, and the keys it adds and removes."""

    from_version: int
    to_version: int
    adds: tuple[str, ...]
    removes: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a step that does not move forwards."""
        if self.to_version <= self.from_version:
            raise ValueError("a migration step must move forwards")


@dataclass(frozen=True)
class Migration:
    """The migrated state, and the steps that got it there."""

    outcome: Outcome
    state: dict
    applied: tuple[int, ...]
    reason: str = ""


def migrate(state: dict, *, to_version: int, steps: tuple[Step, ...]) -> Migration:
    """Bring `state` up to `to_version` using `steps`."""
    if "version" not in state:
        raise ValueError("stored state must say which version it is")

    starts = [step.from_version for step in steps]
    if len(starts) != len(set(starts)):
        raise ValueError("two steps cannot start from the same version")

    by_from = {step.from_version: step for step in steps}
    current = state["version"]

    if current > to_version:
        return Migration(
            Outcome.TOO_NEW,
            state,
            (),
            reason=f"this was written by a newer version ({current})",
        )

    if current == to_version:
        return Migration(Outcome.ALREADY_CURRENT, state, ())

    working = dict(state)
    applied: list[int] = []

    while current < to_version:
        step = by_from.get(current)
        if step is None:
            return Migration(
                Outcome.NO_PATH,
                state,
                (),
                reason=f"there is no way forward from version {current}",
            )
        for field in step.adds:
            working.setdefault(field, None)
        for field in step.removes:
            working.pop(field, None)
        working["version"] = step.to_version
        applied.append(step.to_version)
        current = step.to_version

    return Migration(Outcome.MIGRATED, working, tuple(applied))
