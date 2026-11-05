"""How many calls to one tool may be in flight at the same time."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConcurrencyLimits:
    """How many calls may be in flight, per tool and by default."""

    per_tool: dict[str, int]
    default: int

    def __post_init__(self) -> None:
        """Reject limits that would block every call."""
        if self.default < 1:
            raise ValueError("at least one call must be allowed through")
        if any(limit < 1 for limit in self.per_tool.values()):
            raise ValueError("a tool limited to no calls can never be used")

    def for_tool(self, tool: str) -> int:
        """The limit that applies to `tool`."""
        return self.per_tool.get(tool, self.default)


@dataclass(frozen=True)
class Entry:
    """The outcome of asking to enter the gate for a tool."""

    admitted: bool
    in_flight: int
    limit: int
    reason: str = ""


@dataclass
class Gate:
    """Admits tool calls up to the configured concurrency limits."""

    limits: ConcurrencyLimits
    _in_flight: dict[str, list[str]] = field(default_factory=dict)

    def enter(self, tool: str, *, run: str) -> Entry:
        """Ask to start a call to `tool` on behalf of `run`."""
        if not tool.strip():
            raise ValueError("a call must name its tool")

        holders = self._in_flight.setdefault(tool, [])
        limit = self.limits.for_tool(tool)

        if len(holders) >= limit:
            return Entry(
                admitted=False,
                in_flight=len(holders),
                limit=limit,
                reason=f"{tool} allows {limit} at a time",
            )

        holders.append(run)
        return Entry(admitted=True, in_flight=len(holders), limit=limit)

    def leave(self, tool: str, *, run: str) -> None:
        """Release the slot `run` held for `tool`."""
        holders = self._in_flight.get(tool, [])
        if run in holders:
            holders.remove(run)

    def in_flight_for(self, tool: str) -> int:
        """How many calls to `tool` are in flight."""
        return len(self._in_flight.get(tool, []))
