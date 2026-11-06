"""What a run came back with, read in one place."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.src.agent.config.inbound_pause import paused_result


class RunFailedInBody(RuntimeError):
    """The status said 200 and the body said it threw."""


class NoAnswer(RuntimeError):
    """The run finished and produced nothing to report."""


@dataclass(frozen=True)
class Outcome:
    """What a run came to: its text, thread, and anything it paused on."""

    text: str
    thread_id: str
    paused: dict[str, Any] | None = None


def outcome_of(state: Any, *, thread_id: str) -> Outcome:
    """Read a run reply, or raise with what actually happened."""
    body = state if isinstance(state, dict) else {}

    failure = body.get("__error__")
    if failure is not None:
        raise RunFailedInBody(f"The run failed: {_why(failure)}")

    waiting = paused_result(body, thread_id=thread_id)
    if waiting is not None:
        return Outcome(text="", thread_id=thread_id, paused=waiting)

    text = answer_from(body)
    if text is None:
        raise NoAnswer(f"The run finished without answering (conversation {thread_id})")
    return Outcome(text=text, thread_id=thread_id)


def answer_from(state: dict[str, Any]) -> str | None:
    """The last thing the agent said, or nothing."""
    for message in reversed(state.get("messages") or []):
        if not isinstance(message, dict) or message.get("type") != "ai":
            continue
        said = _text_of(message.get("content"))
        if said:
            return said
    return None


def _text_of(content: Any) -> str | None:
    """The text of a message's content, or `None` if there is none."""
    if isinstance(content, str):
        return content or None
    if isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        joined = "".join(parts)
        return joined or None
    return None


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(
            payload.get("message")
            or payload.get("error")
            or payload
            or "no detail given"
        )
    return str(payload)
