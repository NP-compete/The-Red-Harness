"""Problems found while reading configuration, kept to be asked about."""

from __future__ import annotations

from dataclasses import dataclass

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


@dataclass(frozen=True)
class ConfigProblem:
    """One problem found reading the config tree."""

    source: str
    detail: str


_found: dict[tuple[str, str], ConfigProblem] = {}


def note_problem(source: str, detail: str) -> None:
    """Remember something wrong with a file the agent is still using."""
    key = (source, detail)
    if key in _found:
        return
    _found[key] = ConfigProblem(source=source, detail=detail)


def found_problems() -> list[ConfigProblem]:
    """Every problem found so far."""
    return list(_found.values())


def reset_problems() -> None:
    """Forget everything, for a fresh read of the tree."""
    _found.clear()
