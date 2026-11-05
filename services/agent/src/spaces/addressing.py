"""Whether a message in a room is for the agent (E33-T3)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Addressing:
    """Whether a message is for the agent, and why."""

    addressed: bool
    reason: str


def _handle_pattern(handle: str) -> re.Pattern[str]:
    """A pattern matching `@handle` as a whole word."""
    return re.compile(rf"(?<![\w@.]){re.escape('@' + handle)}\b", re.IGNORECASE)


def addresses_agent(text: str, *, handle: str, always_on: bool = False) -> Addressing:
    """Is this message for the agent?"""
    if always_on:
        return Addressing(True, "always_on")

    if not text or not handle:
        return Addressing(False, "not_addressed")

    if _handle_pattern(handle).search(text):
        return Addressing(True, "tagged")

    return Addressing(False, "not_addressed")
