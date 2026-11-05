"""Comparing a server as it is now against the server that was trusted."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Trust(Enum):
    """How a server compares to the one that was approved."""

    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"
    MOVED = "moved"
    CERTIFICATE_CHANGED = "certificate-changed"
    TOOLS_CHANGED = "tools-changed"
    INSECURE = "insecure"


@dataclass(frozen=True)
class Known:
    """An MCP server as it was when it was approved."""

    name: str
    url: str
    certificate_fingerprint: str
    tool_count: int


@dataclass(frozen=True)
class Seen:
    """An MCP server as it presents itself now."""

    name: str
    url: str
    certificate_fingerprint: str
    tool_count: int

    def __post_init__(self) -> None:
        """Reject a server with no name."""
        if not self.name.strip():
            raise ValueError("a server must have a name")


@dataclass(frozen=True)
class Check:
    """Whether a server is still usable, and why not."""

    trust: Trust
    usable: bool
    reason: str = ""


def check_server(seen: Seen, *, known: Known | None) -> Check:
    """Compare `seen` against the approved `known` server."""
    if known is not None and known.name != seen.name:
        raise ValueError("two different servers cannot be compared")

    if not seen.url.lower().startswith("https://"):
        return Check(Trust.INSECURE, False, f"{seen.url} is not encrypted")

    if known is None:
        return Check(Trust.UNKNOWN, False, f"{seen.name} has not been connected before")

    if known.certificate_fingerprint != seen.certificate_fingerprint:
        return Check(
            Trust.CERTIFICATE_CHANGED,
            False,
            f"{seen.name} is presenting a different certificate",
        )

    if known.url != seen.url:
        return Check(
            Trust.MOVED, False, f"{seen.name} moved from {known.url} to {seen.url}"
        )

    if known.tool_count != seen.tool_count:
        gained = seen.tool_count > known.tool_count
        return Check(
            Trust.TOOLS_CHANGED,
            not gained,
            f"{seen.name} now offers {seen.tool_count} tools, was {known.tool_count}",
        )

    return Check(Trust.UNCHANGED, True)
