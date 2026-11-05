"""Read an agent's own conversations for things worth looking at."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agent.src.improvement.mine import Observation, mine


class ObserveFailed(RuntimeError):
    """The conversations could not be listed."""


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        ...


@dataclass
class Findings:
    """What was observed across the conversations that could be read."""

    observations: list[Observation] = field(default_factory=list)
    read: int = 0
    runs: list[Any] = field(default_factory=list)
    unreadable: int = 0


def collect(
    *, transport: Transport, limit: int = 100, since: str | None = None
) -> Findings:
    """Gather observations across the agent's conversations."""
    status, payload = transport.get("/threads")
    if status != 200:
        raise ObserveFailed(f"Could not list conversations ({status}): {_why(payload)}")

    threads = _threads_in(payload)
    if threads is None:
        raise ObserveFailed("The agent answered with something that is not a list")

    runs: list[dict[str, Any]] = []
    unreadable = 0
    for thread in threads[:limit]:
        if not isinstance(thread, dict):
            continue
        thread_id = str(thread.get("thread_id") or "")
        status, state = transport.get(f"/threads/{thread_id}/state")
        if status != 200 or not isinstance(state, dict):
            unreadable += 1
            continue
        messages = (state.get("values") or {}).get("messages") or []
        if not messages:
            continue
        runs.append(
            {
                "run_id": thread_id,
                "messages": messages,
                "created_at": thread.get("created_at"),
            }
        )

    return Findings(
        observations=mine(runs, since=since),
        read=len(runs),
        unreadable=unreadable,
        runs=runs,
    )


def proposals_for(
    found: Findings, *, transport: Transport, max_per_run: int | None = None
) -> list[Any]:
    """What those observations suggest changing (E12-T3)."""
    from urllib.parse import quote

    from agent.src.improvement.generate import (
        AGENT_CONFIG,
        MAX_PER_RUN,
        generate,
    )

    status, payload = transport.get(f"/config/file?path={quote(AGENT_CONFIG, safe='')}")
    if status != 200 or not isinstance(payload, dict):
        raise ObserveFailed(
            f"Could not read {AGENT_CONFIG} ({status}): {_why(payload)}. "
            "Observations are above; there is nothing to diff them against."
        )

    from dataclasses import replace

    from agent.src.improvement.probe import probe

    made = generate(
        found.observations,
        config_text=str(payload.get("content") or ""),
        max_per_run=max_per_run or MAX_PER_RUN,
    )
    return [
        replace(one, probe=probe(one, found.runs)) if one.diff else one for one in made
    ]


def _threads_in(payload: Any) -> list | None:
    """The list of threads in a payload, however it is wrapped."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("threads"), list):
        rows: list[Any] = payload["threads"]
        return rows
    return None


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(payload.get("detail") or payload.get("message") or payload)
    return str(payload)
