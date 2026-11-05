"""Noticing when a run has stopped producing anything."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class State(Enum):
    """Whether a run is getting anywhere."""

    WORKING = "working"
    STALLED = "stalled"
    TOOL_HUNG = "tool-hung"
    WAITING = "waiting"


@dataclass(frozen=True)
class Activity:
    """When a run last did anything, and how long to give it."""

    last_output_at: datetime
    last_tool_started_at: datetime | None
    waiting_on_person: bool
    tool_running: str
    patience: timedelta

    def __post_init__(self) -> None:
        """Reject no patience at all, or a running tool with no start time."""
        if self.patience <= timedelta(0):
            raise ValueError("a run needs some time before it counts as stalled")
        if self.tool_running and self.last_tool_started_at is None:
            raise ValueError("a running tool must say when it started")


@dataclass(frozen=True)
class Stall:
    """Whether a run has stalled, and for how long."""

    state: State
    quiet_for: timedelta
    needs_attention: bool
    reason: str = ""


def check_stall(activity: Activity, *, now: datetime) -> Stall:
    """Decide whether `activity` amounts to a stall as of `now`."""
    quiet = max(timedelta(0), now - activity.last_output_at)

    if activity.waiting_on_person:
        return Stall(State.WAITING, quiet, needs_attention=False)

    if activity.tool_running and activity.last_tool_started_at is not None:
        running = now - activity.last_tool_started_at
        if running > activity.patience:
            return Stall(
                State.TOOL_HUNG,
                quiet,
                needs_attention=True,
                reason=f"{activity.tool_running} has been running for {int(running.total_seconds())}s",
            )
        return Stall(State.WORKING, quiet, needs_attention=False)

    if quiet > activity.patience:
        return Stall(
            State.STALLED,
            quiet,
            needs_attention=True,
            reason=f"nothing has happened for {int(quiet.total_seconds())}s",
        )

    return Stall(State.WORKING, quiet, needs_attention=False)
