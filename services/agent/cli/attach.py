"""Picking an answer back up after the connection went (E28-T4)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Callable, Protocol

from agent.cli.ask import Answer
from agent.cli.outcome import outcome_of


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        ...

    def stream(
        self, path: str, body: dict | None = None, method: str = "POST"
    ) -> Iterator[str]:
        """Stream `path`, yielding lines as they arrive."""
        ...


class AttachFailed(RuntimeError):
    """There is nothing to attach to."""


def attach(
    thread_id: str,
    run_id: str,
    *,
    transport: Transport,
    follow: bool = False,
    write: Callable[[str], None] | None = None,
) -> Answer:
    """Whatever that run produces, from wherever it has got to."""
    where = f"/threads/{thread_id}/runs/{run_id}"

    if follow:
        from agent.cli.follow import follow as read_stream

        said = write or (lambda piece: print(piece, end="", flush=True))
        try:
            lines = transport.stream(f"{where}/stream", method="GET")
            watched = read_stream(lines, thread_id=thread_id, write=said)
        except RuntimeError as refused:
            raise AttachFailed(_missing(thread_id, run_id, refused)) from None
        if watched.text or watched.paused:
            return Answer(text=watched.text, thread_id=thread_id, paused=watched.paused)

    status, state = transport.get(f"{where}/join")
    if status == 404:
        raise AttachFailed(_missing(thread_id, run_id, "no such run"))
    if status not in (200, 201):
        raise AttachFailed(f"Could not attach to {run_id} ({status})")
    found = outcome_of(state, thread_id=thread_id)
    return Answer(text=found.text, thread_id=thread_id, paused=found.paused)


def _missing(thread_id: str, run_id: str, why: Any) -> str:
    """The message explaining that a run is not on this conversation."""
    return (
        f"{run_id} is not a run on conversation {thread_id} ({why}). "
        "`harness run list <thread>` shows the ones that are."
    )
