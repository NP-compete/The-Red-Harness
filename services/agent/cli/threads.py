"""Conversations, over the public surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ThreadFailed(RuntimeError):
    """The agent would not, or could not, answer."""


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        ...

    def post(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        ...

    def delete(self, path: str) -> tuple[int, Any]:
        """DELETE `path` and return the status and decoded body."""
        ...


@dataclass(frozen=True)
class ThreadRow:
    """One thread, as listed."""

    thread_id: str
    title: str
    status: str


def list_threads(*, transport: Transport) -> list[ThreadRow]:
    """Every conversation the caller may see."""
    status, payload = transport.get("/threads")
    if status != 200:
        raise ThreadFailed(f"Could not list conversations ({status}): {_why(payload)}")
    rows = _rows_in(payload)
    if rows is None:
        raise ThreadFailed("The agent answered with something that is not a list")

    return [
        ThreadRow(
            thread_id=str(row.get("thread_id", "")),
            title=str((row.get("metadata") or {}).get("thread_name") or ""),
            status=str(row.get("status") or ""),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _rows_in(payload: Any) -> list | None:
    """The conversations, whichever shape they arrived in."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("threads"), list):
        rows: list[Any] = payload["threads"]
        return rows
    return None


def show_thread(thread_id: str, *, transport: Transport) -> dict:
    """The stored state of one thread."""
    status, payload = transport.get(f"/threads/{thread_id}/state")
    if status != 200:
        raise ThreadFailed(f"Could not read {thread_id} ({status}): {_why(payload)}")
    return payload if isinstance(payload, dict) else {}


def remove_thread(thread_id: str, *, transport: Transport) -> None:
    """Remove it, or accept that it is already gone."""
    status, payload = transport.delete(f"/threads/{thread_id}")
    if status in (200, 202, 204, 404):
        return
    raise ThreadFailed(f"Could not remove {thread_id} ({status}): {_why(payload)}")


def fork_thread(thread_id: str, *, transport: Transport, at: int | None = None) -> str:
    """Copy a conversation, by default the whole of it."""
    if at is None:
        held = show_thread(thread_id, transport=transport)
        at = len((held.get("values") or {}).get("messages") or [])
    body: dict[str, Any] = {"message_index": at}
    status, payload = transport.post(f"/threads/{thread_id}/fork", body)
    if status not in (200, 201):
        raise ThreadFailed(f"Could not fork {thread_id} ({status}): {_why(payload)}")
    made = (payload or {}).get("thread_id") if isinstance(payload, dict) else None
    if not made:
        raise ThreadFailed(
            "The agent forked the conversation but did not name the copy"
        )
    return str(made)


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(payload.get("detail") or payload.get("message") or payload)
    return str(payload)
