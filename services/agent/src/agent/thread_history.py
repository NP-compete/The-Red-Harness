"""The shape of a conversation, read from its checkpoints."""

from __future__ import annotations

from typing import Any

Entry = dict[str, Any]


def _messages(entry: Entry) -> list[Any]:
    return (entry.get("values") or {}).get("messages") or []


def shown_messages(history: list[Entry]) -> list[Any]:
    """The conversation as it stands — what a reader is looking at."""
    for entry in history:
        found = _messages(entry)
        if found:
            return list(found)
    return []


def high_water_mark(history: list[Entry]) -> int:
    """The most messages this conversation ever held at once."""
    return max((len(_messages(entry)) for entry in history), default=0)


def was_shortened(history: list[Entry]) -> bool:
    """Whether something has removed messages from this conversation."""
    return high_water_mark(history) > len(shown_messages(history))
