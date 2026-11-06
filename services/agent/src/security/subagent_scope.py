"""Bounding what a subagent inherits from the agent that called it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Subagent:
    """One subagent, the tools it may use, and whether it writes."""

    name: str
    tools: list[str]
    writes: bool

    def __post_init__(self) -> None:
        """Reject a subagent with no name."""
        if not self.name.strip():
            raise ValueError("a subagent needs a name")


@dataclass(frozen=True)
class Scope:
    """What a subagent may actually do, and what was refused."""

    tools: tuple[str, ...]
    refused: tuple[str, ...]
    tainted: bool
    calls_remaining: int


def scope_for(
    subagent: Subagent,
    *,
    parent_tools: list[str],
    acting_tools: list[str] | None = None,
    parent_tainted: bool = False,
    parent_calls_remaining: int = 0,
    requested_calls: int | None = None,
) -> Scope:
    """Work out what `subagent` may do, never beyond its parent."""
    available = set(parent_tools)
    acting = set(acting_tools or [])

    granted = sorted(
        tool
        for tool in subagent.tools
        if tool in available and (subagent.writes or tool not in acting)
    )
    refused = tuple(sorted(set(subagent.tools) - set(granted)))

    budget = parent_calls_remaining
    if requested_calls is not None:
        budget = min(budget, requested_calls)

    return Scope(
        tools=tuple(granted),
        refused=refused,
        tainted=parent_tainted,
        calls_remaining=budget,
    )
