"""What the rest of a plan does when one task fails."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Fate(Enum):
    """What became of a task after another one failed."""

    FAILED = "failed"
    SKIPPED = "skipped"
    CONTINUES = "continues"


@dataclass(frozen=True)
class Task:
    """One task in a plan, what it needs, and whether it is optional."""

    name: str
    needs: tuple[str, ...] = ()
    optional: bool = False


@dataclass(frozen=True)
class Aftermath:
    """What survives a failure, and whether to abandon the plan."""

    fates: dict[str, Fate]
    skipped: tuple[str, ...]
    abandon: bool
    partial_result: bool
    reason: str


def after_failure(plan: list[Task], *, failed: str) -> Aftermath:
    """Work out what can still run after `failed` failed."""
    if not plan:
        raise ValueError("there is no plan to work through")

    by_name = {task.name: task for task in plan}
    if failed not in by_name:
        raise ValueError(f"{failed} is not in this plan")

    lost = set() if by_name[failed].optional else _dependents(by_name, failed)

    fates = {
        name: Fate.FAILED
        if name == failed
        else Fate.SKIPPED
        if name in lost
        else Fate.CONTINUES
        for name in by_name
    }

    continuing = [name for name, fate in fates.items() if fate is Fate.CONTINUES]

    return Aftermath(
        fates=fates,
        skipped=tuple(sorted(lost)),
        abandon=not continuing,
        partial_result=bool(continuing),
        reason=(
            f"{failed} failed and nothing else can be done"
            if not continuing
            else f"{failed} failed; the rest of the work carries on"
        ),
    )


def _dependents(by_name: dict[str, Task], failed: str) -> set[str]:
    """Every task that transitively depends on `failed`."""
    lost: set[str] = set()
    frontier = {failed}

    while frontier:
        nxt = {
            task.name
            for task in by_name.values()
            if task.name not in lost
            and task.name != failed
            and any(
                need in frontier and not by_name[need].optional for need in task.needs
            )
        }
        lost |= nxt
        frontier = nxt

    return lost
