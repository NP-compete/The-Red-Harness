"""Settings that still work and are going away."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from agent.src.agent.config.paths import _CANDIDATES
from agent.src.agent.config.problems import note_problem
from agent.src.agent.config.schema_version import CURRENT

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Deprecation:
    """One setting on its way out, and what to do about it."""

    what: str
    instead: str | None
    removed_in: int

    def render(self) -> str:
        """The deprecation as one sentence."""
        move = f" — use {self.instead}" if self.instead else ""
        return f"{self.what} is deprecated{move}; it goes in schema version {self.removed_in}"


FIELDS: tuple[Deprecation, ...] = ()


def _legacy_paths(config_dir: Path) -> list[Deprecation]:
    """Files still at a pre-rename path."""
    found = []
    for name, candidates in _CANDIDATES.items():
        preferred, *older = candidates
        for path in older:
            if (config_dir / path).is_file() and not (config_dir / preferred).is_file():
                found.append(
                    Deprecation(
                        what=path,
                        instead=preferred,
                        removed_in=CURRENT + 1,
                    )
                )
    return found


def deprecations_in(
    raw: dict,
    config_dir: Path,
    *,
    fields: tuple[Deprecation, ...] = FIELDS,
) -> list[Deprecation]:
    """Everything in this tree that is on its way out."""
    found = _legacy_paths(config_dir)

    for entry in fields:
        section, _, field = entry.what.rpartition(".")
        holder = raw.get(section) if section else raw
        if isinstance(holder, dict) and field in holder:
            found.append(entry)

    return found


_said: set[str] = set()


def warn_once(found: list[Deprecation]) -> None:
    """Log and record each one, at most once in this process."""
    for entry in found:
        if entry.what in _said:
            continue
        _said.add(entry.what)
        logger.warning("%s", entry.render())
        note_problem("configuration", entry.render())


def reset_warnings() -> None:
    """Forget what has been said. For tests."""
    _said.clear()
