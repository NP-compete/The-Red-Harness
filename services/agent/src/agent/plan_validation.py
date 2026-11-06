"""Checking a plan holds together before any of it runs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Problem(Enum):
    """One thing wrong with a plan's dependencies."""

    MISSING_DEPENDENCY = "missing-dependency"
    CIRCULAR = "circular"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class Task:
    """One task in a plan, and what it waits on."""

    name: str
    needs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject a task with no name."""
        if not self.name.strip():
            raise ValueError("a task must have a name")


@dataclass(frozen=True)
class Validation:
    """Whether a plan holds together, and the order it would run in."""

    sound: bool
    problems: tuple[Problem, ...]
    order: tuple[str, ...]
    stages: tuple[tuple[str, ...], ...]
    depth: int
    detail: str = ""


def validate_plan(tasks: list[Task]) -> Validation:
    """Check `tasks` for missing, circular and duplicate dependencies."""
    if not tasks:
        raise ValueError("a plan must have something in it")

    problems: list[Problem] = []
    notes: list[str] = []

    names = [task.name for task in tasks]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        problems.append(Problem.DUPLICATE)
        notes.append(f"listed more than once: {', '.join(duplicates)}")

    by_name = {task.name: task for task in tasks}
    missing = sorted(
        {need for task in tasks for need in task.needs if need not in by_name}
    )
    if missing:
        problems.append(Problem.MISSING_DEPENDENCY)
        notes.append(f"nothing provides: {', '.join(missing)}")

    stages, stuck = _stages(by_name)
    if stuck:
        problems.append(Problem.CIRCULAR)
        notes.append(f"these wait on each other: {', '.join(sorted(stuck))}")

    usable = not stuck and not missing

    return Validation(
        sound=not problems,
        problems=tuple(problems),
        order=tuple(name for stage in stages for name in stage) if usable else (),
        stages=stages if usable else (),
        depth=len(stages) if usable else 0,
        detail="; ".join(notes),
    )


def _stages(by_name: dict[str, Task]) -> tuple[tuple[tuple[str, ...], ...], set[str]]:
    """The tasks grouped into stages that can run together, and what is stuck."""
    waiting = {
        name: {need for need in task.needs if need in by_name}
        for name, task in by_name.items()
    }
    stages: list[tuple[str, ...]] = []
    done: set[str] = set()

    while True:
        ready = sorted(name for name, needs in waiting.items() if needs <= done)
        if not ready:
            break
        stages.append(tuple(ready))
        done.update(ready)
        for name in ready:
            waiting.pop(name)

    return tuple(stages), set(waiting)
