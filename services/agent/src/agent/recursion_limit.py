"""How deep agents may call other agents, and when that is a cycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Refusal(Enum):
    """Why a subagent was not allowed to start."""

    CYCLE = "cycle"
    TOO_DEEP = "too-deep"
    TOO_MANY = "too-many"


@dataclass(frozen=True)
class Spawn:
    """A request to start a subagent, and the chain above it."""

    parent: str
    child: str
    ancestry: tuple[str, ...]
    max_depth: int
    siblings_running: int
    max_siblings: int

    def __post_init__(self) -> None:
        """Reject no room at all, or an ancestry that does not end at the parent."""
        if self.max_depth < 1:
            raise ValueError("there must be room for at least one agent")
        if not self.ancestry or self.ancestry[-1] != self.parent:
            raise ValueError("the parent must be the last agent in the ancestry")


@dataclass(frozen=True)
class Decision:
    """Whether the subagent may start, and how deep it would be."""

    permitted: bool
    depth: int
    depth_remaining: int
    refusal: Refusal | None = None
    reason: str = ""


def may_spawn(spawn: Spawn) -> Decision:
    """Decide whether `spawn` may go ahead."""
    depth = len(spawn.ancestry) + 1
    remaining = max(0, spawn.max_depth - depth)

    def refuse(refusal: Refusal, reason: str) -> Decision:
        """A refusal with this code and reason."""
        return Decision(False, depth, remaining, refusal, reason)

    if spawn.child in spawn.ancestry:
        return refuse(
            Refusal.CYCLE,
            f"{spawn.child} is already running further up this chain",
        )

    if depth > spawn.max_depth:
        return refuse(
            Refusal.TOO_DEEP,
            f"agents may only nest {spawn.max_depth} deep",
        )

    if spawn.siblings_running >= spawn.max_siblings:
        return refuse(
            Refusal.TOO_MANY,
            f"{spawn.siblings_running} agents are already running here",
        )

    return Decision(True, depth, remaining)
