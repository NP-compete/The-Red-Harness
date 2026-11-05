"""Runs, for whoever is holding the pager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class RunFailed(RuntimeError):
    """The agent would not, or could not, answer."""


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        ...

    def post(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        ...


SETTLED = frozenset(
    {"success", "error", "cancelled", "canceled", "timeout", "interrupted"}
)


@dataclass(frozen=True)
class RunRow:
    """One run of a thread, as listed."""

    run_id: str
    status: str
    error: str
    created_at: str


def list_runs(thread_id: str, *, transport: Transport) -> list[RunRow]:
    """Every run of `thread_id`."""
    status, payload = transport.get(f"/threads/{thread_id}/runs")
    if status != 200:
        raise RunFailed(
            f"Could not list runs for {thread_id} ({status}): {_why(payload)}"
        )

    rows = _rows_in(payload)
    if rows is None:
        raise RunFailed("The agent answered with something that is not a list of runs")

    return [
        RunRow(
            run_id=str(row.get("run_id", "")),
            status=str(row.get("status") or ""),
            error=str(row.get("error_message") or ""),
            created_at=str(row.get("created_at") or ""),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def show_run(thread_id: str, run_id: str, *, transport: Transport) -> dict:
    """The stored detail of one run."""
    status, payload = transport.get(f"/threads/{thread_id}/runs/{run_id}")
    if status != 200:
        raise RunFailed(f"Could not read run {run_id} ({status}): {_why(payload)}")
    return payload if isinstance(payload, dict) else {}


def cancel_run(thread_id: str, run_id: str, *, transport: Transport) -> None:
    """Stop it, or accept that it already stopped."""
    status, payload = transport.post(f"/threads/{thread_id}/runs/{run_id}/cancel", {})
    if status in (200, 202, 204, 404):
        return
    raise RunFailed(f"Could not cancel run {run_id} ({status}): {_why(payload)}")


def unfinished(rows: list[RunRow]) -> list[RunRow]:
    """The runs that have not stopped."""
    return [row for row in rows if row.status.lower() not in SETTLED]


def _rows_in(payload: Any) -> list | None:
    """The list of rows in a payload, however it is wrapped."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("runs"), list):
        rows: list[Any] = payload["runs"]
        return rows
    return None


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(payload.get("detail") or payload.get("message") or payload)
    return str(payload)
