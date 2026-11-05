"""Answering a run that stopped for a decision."""

from __future__ import annotations

from typing import Any, Protocol

from agent.cli.ask import Answer
from agent.cli.outcome import (
    NoAnswer,
    RunFailedInBody,
    answer_from,
    outcome_of,
)

DECISIONS = ("approve", "edit", "reject", "respond")


class ResumeFailed(RuntimeError):
    """The decision was not accepted, or produced nothing."""


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def post(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        ...


def resume_run(
    thread_id: str,
    decision: str,
    *,
    transport: Transport,
    message: str = "",
    assistant_id: str = "agent",
) -> Answer:
    """Send one decision and wait for what happens next."""
    if decision not in DECISIONS:
        raise ResumeFailed(
            f"{decision!r} is not a decision this agent takes. "
            f"Use one of: {', '.join(DECISIONS)}."
        )

    sent: dict[str, Any] = {"type": decision}
    if message:
        sent["message"] = message

    status, state = transport.post(
        f"/threads/{thread_id}/runs/wait",
        {"assistant_id": assistant_id, "command": {"resume": {"decisions": [sent]}}},
    )
    if status not in (200, 201):
        raise ResumeFailed(f"The run would not continue ({status}): {_why(state)}")

    try:
        found = outcome_of(state, thread_id=thread_id)
        if found.paused is not None:
            return Answer(text="", thread_id=thread_id, paused=found.paused)
        return Answer(text=found.text, thread_id=thread_id)
    except RunFailedInBody as threw:
        raise ResumeFailed(str(threw)) from None
    except NoAnswer:
        pass

    stored = _messages_of(_conversation(thread_id, transport=transport))
    text = answer_from(stored)
    if text is None:
        raise ResumeFailed(
            f"The run continued but said nothing (conversation {thread_id})"
        )
    return Answer(text=text, thread_id=thread_id)


def _conversation(thread_id: str, *, transport: Any) -> dict[str, Any]:
    """The state of `thread_id`, read back after a decision."""
    status, state = transport.get(f"/threads/{thread_id}/state")
    if status != 200 or not isinstance(state, dict):
        raise ResumeFailed(
            f"The decision was accepted but conversation {thread_id} could "
            f"not be read back ({status})"
        )
    return state


def _messages_of(state: Any) -> dict[str, Any]:
    """The transcript, wherever this shape keeps it."""
    if not isinstance(state, dict):
        return {}
    if state.get("messages"):
        return state
    return {"messages": (state.get("values") or {}).get("messages") or []}


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(payload.get("detail") or payload.get("message") or payload)
    return str(payload)
