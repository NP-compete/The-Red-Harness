"""Watching an answer arrive, rather than waiting for it (E28-T4)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

TEXT_EVENTS = ("messages/partial", "messages/complete", "messages")


@dataclass(frozen=True)
class Followed:
    """What the stream turned out to be."""

    text: str
    thread_id: str
    paused: dict[str, Any] | None = None


def text_in(event: str, data: Any) -> str:
    """The words in one frame, or nothing."""
    if event not in TEXT_EVENTS:
        return ""
    found = data[0] if isinstance(data, list) and data else data
    if not isinstance(found, dict):
        return ""
    if found.get("type") not in (None, "ai", "AIMessageChunk"):
        return ""
    content = found.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return ""


def pause_in(data: Any, *, thread_id: str) -> dict[str, Any] | None:
    """The decision a frame is waiting on, if it is waiting."""
    from agent.src.agent.config.inbound_pause import paused_result

    if isinstance(data, dict):
        return paused_result(data, thread_id=thread_id)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return pause_in(data[0], thread_id=thread_id)
    return None


def follow(
    lines: Iterator[str], *, thread_id: str, write: Callable[[str], None]
) -> Followed:
    """Read an SSE stream, printing text as it arrives."""
    event = ""
    said: list[str] = []
    paused: dict[str, Any] | None = None

    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("event:"):
            event = line[len("event:") :].strip()
            continue
        if not line.startswith("data:"):
            continue

        raw = line[len("data:") :].strip()
        if raw in ("", "[DONE]"):
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        waiting = pause_in(data, thread_id=thread_id)
        if waiting is not None:
            paused = waiting
            break

        piece = text_in(event, data)
        if piece:
            whole = "".join(said)
            if piece.startswith(whole):
                piece = piece[len(whole) :]
                said.append(piece)
            else:
                said.append(piece)
            if piece:
                write(piece)

    return Followed(text="".join(said), thread_id=thread_id, paused=paused)
