"""Tracks whether a run has read content the deployment does not vouch for."""

from __future__ import annotations

from dataclasses import dataclass

from agent.src.security.resolver import RunContext, Trust


@dataclass(frozen=True)
class ToolResult:
    """What a tool returned, and which server it came from."""

    tool_name: str
    server: str | None = None


class RunTrust:
    """Tracks whether a run has read anything from an untrusted server."""

    def __init__(self, trusted_servers: list[str]) -> None:
        """Start clean, treating `trusted_servers` as safe to read from."""
        self._trusted = frozenset(trusted_servers)
        self._sources: list[str] = []

    @property
    def level(self) -> Trust:
        """The trust level the run has fallen to."""
        return Trust.UNTRUSTED_READ if self._sources else Trust.CLEAN

    @property
    def sources(self) -> tuple[str, ...]:
        """The untrusted tool results this run has read, in order."""
        return tuple(self._sources)

    def record(self, result: ToolResult) -> None:
        """Note a tool result, dropping trust if its server is untrusted."""
        if result.server is None or result.server in self._trusted:
            return
        self._sources.append(f"{result.server}.{result.tool_name}")

    def apply(self, ctx: RunContext) -> RunContext:
        """Return `ctx` marked untrusted if this run has read untrusted content."""
        if self.level is Trust.CLEAN:
            return ctx
        return ctx.with_untrusted_read()
