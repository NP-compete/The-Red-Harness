"""Ask one question and wait for the answer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent.cli.outcome import answer_from  # noqa: F401


class AskFailed(RuntimeError):
    """The question did not produce an answer, and why."""


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def post(self, path: str, body: dict | None = None) -> tuple[int, dict]:
        """POST `body` to `path` and return the status and decoded body."""
        ...


@dataclass(frozen=True)
class Answer:
    """What the agent answered, and the thread it answered in."""

    text: str
    thread_id: str
    paused: dict[str, Any] | None = None


def ask(
    question: str,
    *,
    transport: Transport,
    assistant_id: str = "agent",
) -> Answer:
    """Put `question` to the agent in a fresh conversation."""
    status, made = transport.post("/threads", {})
    if status not in (200, 201):
        raise AskFailed(f"Could not start a conversation ({status}): {_why(made)}")

    thread_id = made.get("thread_id")
    if not thread_id:
        raise AskFailed("The agent made a conversation but did not name it")

    status, state = transport.post(
        f"/threads/{thread_id}/runs/wait",
        {
            "assistant_id": assistant_id,
            "input": {"messages": [{"role": "human", "content": question}]},
        },
    )
    if status not in (200, 201):
        raise AskFailed(f"The run failed ({status}): {_why(state)}")

    from agent.cli.outcome import NoAnswer, RunFailedInBody, outcome_of

    try:
        found = outcome_of(state, thread_id=thread_id)
    except (RunFailedInBody, NoAnswer) as wrong:
        raise AskFailed(str(wrong)) from None

    return Answer(text=found.text, thread_id=thread_id, paused=found.paused)


def ask_following(
    question: str,
    *,
    transport: Any,
    write: Any,
    assistant_id: str = "agent",
) -> Answer:
    """Ask, and print the answer as it arrives (E28-T4)."""
    from agent.cli.follow import follow

    status, made = transport.post("/threads", {})
    if status not in (200, 201):
        raise AskFailed(f"Could not start a conversation ({status}): {_why(made)}")

    thread_id = made.get("thread_id")
    if not thread_id:
        raise AskFailed("The agent made a conversation but did not name it")

    try:
        lines = transport.stream(
            f"/threads/{thread_id}/runs/stream",
            {
                "assistant_id": assistant_id,
                "input": {"messages": [{"role": "human", "content": question}]},
                "stream_mode": ["messages", "values"],
            },
        )
        found = follow(lines, thread_id=thread_id, write=write)
    except Exception as failed:
        raise AskFailed(f"The run failed while streaming: {failed}") from None

    if not found.text and found.paused is None:
        raise AskFailed("The agent streamed no answer")

    return Answer(text=found.text, thread_id=thread_id, paused=found.paused)


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(payload.get("detail") or payload.get("message") or payload)
    return str(payload)
