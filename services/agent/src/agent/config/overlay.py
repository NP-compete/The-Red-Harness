"""Edits to configuration, kept as versions rather than as files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class NothingToRevertTo(LookupError):
    """A revert named a version this path has never had."""


@dataclass(frozen=True)
class Version:
    """One recorded state of a config file, and who put it there."""

    path: str
    content: str | None
    version: int
    author: str
    at: str


class Overlay(Protocol):
    """A store of edits layered over the config files shipped with the agent."""

    @property
    def generation(self) -> int:
        """How many times anything in the overlay has changed."""
        ...

    def apply(self, path: str, content: str, *, author: str) -> Version:
        """Record `content` as the new state of `path`."""
        ...

    def adopt_baseline(self, path: str, *, author: str) -> Version:
        """Drop the override on `path` and fall back to the shipped file."""
        ...

    def revert(self, path: str, *, to: int, author: str) -> Version:
        """Record the content of version `to` as a new version of `path`."""
        ...

    def current(self, path: str) -> str | None:
        """The overriding content of `path`, or `None` if it is not overridden."""
        ...

    def at_version(self, path: str, version: int) -> Version:
        """The recorded version `version` of `path`."""
        ...

    def history(self, path: str) -> list[Version]:
        """Every recorded version of `path`, oldest first."""
        ...

    def overridden(self) -> list[str]:
        """Paths the overlay currently overrides."""
        ...


def _now() -> str:
    """The current UTC time, ISO-formatted."""
    return datetime.now(timezone.utc).isoformat()


class InMemoryOverlay:
    """An overlay held in this process."""

    def __init__(self) -> None:
        """Start with no versions recorded."""
        self._versions: dict[str, list[Version]] = {}
        self._generation = 0

    @property
    def generation(self) -> int:
        """How many times anything here has changed."""
        return self._generation

    def _write(self, path: str, content: str | None, author: str) -> Version:
        """Record a new version of `path` and bump the generation."""
        if not author or not author.strip():
            raise ValueError("an edit has to record who made it")

        kept = self._versions.setdefault(path, [])
        written = Version(
            path=path,
            content=content,
            version=len(kept) + 1,
            author=author.strip(),
            at=_now(),
        )
        kept.append(written)
        self._generation += 1
        return written

    def apply(self, path: str, content: str, *, author: str) -> Version:
        """Record `content` as the new state of `path`."""
        return self._write(path, content, author)

    def adopt_baseline(self, path: str, *, author: str) -> Version:
        """Drop the override on `path` and fall back to the shipped file."""
        return self._write(path, None, author)

    def revert(self, path: str, *, to: int, author: str) -> Version:
        """Record the content of version `to` as a new version of `path`."""
        kept = self._versions.get(path) or []
        wanted = next((one for one in kept if one.version == to), None)
        if wanted is None:
            raise NothingToRevertTo(f"{path} has no version {to} to go back to")
        return self._write(path, wanted.content, author)

    def current(self, path: str) -> str | None:
        """The overriding content of `path`, or `None` if it is not overridden."""
        kept = self._versions.get(path) or []
        return kept[-1].content if kept else None

    def at_version(self, path: str, version: int) -> Version:
        """The recorded version `version` of `path`."""
        kept = self._versions.get(path) or []
        found = next((one for one in kept if one.version == version), None)
        if found is None:
            raise NothingToRevertTo(f"{path} has no version {version}")
        return found

    def history(self, path: str) -> list[Version]:
        """Every recorded version of `path`, oldest first."""
        return list(self._versions.get(path) or [])

    def overridden(self) -> list[str]:
        """Paths the overlay currently overrides, in a stable order."""
        return sorted(path for path in self._versions if self.current(path) is not None)
