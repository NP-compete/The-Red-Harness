"""Which remembered things may be used where."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Memory:
    """One remembered fact, who owns it and how far it is shared."""

    key: str
    text: str
    owner: str
    org: str
    team: str
    shared_with_team: bool
    sensitive: bool

    def __post_init__(self) -> None:
        """Reject a memory with no key."""
        if not self.key.strip():
            raise ValueError("a memory needs a key")


@dataclass(frozen=True)
class Place:
    """Where a memory might be used, and who would see it."""

    reader: str
    org: str
    team: str
    shared_thread: bool


def _reachable(memory: Memory, at: Place) -> bool:
    """Whether `memory` is within reach at `at` at all."""
    if memory.org != at.org:
        return False
    if memory.owner == at.reader:
        return True
    return memory.shared_with_team and memory.team == at.team


def usable_here(memories: list[Memory], *, at: Place) -> list[str]:
    """The memories that may actually be used at `at`."""
    usable = []
    for memory in memories:
        if not _reachable(memory, at):
            continue
        if at.shared_thread:
            if memory.sensitive or not (
                memory.shared_with_team and memory.team == at.team
            ):
                continue
        elif memory.sensitive and memory.owner != at.reader:
            continue
        usable.append(memory.key)
    return usable
