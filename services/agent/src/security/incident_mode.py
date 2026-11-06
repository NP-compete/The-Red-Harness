"""What the platform will still do while an incident is open."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Level(Enum):
    """How bad an incident is."""

    DEGRADED = "degraded"
    SEVERE = "severe"


@dataclass(frozen=True)
class Incident:
    """A declared incident, who declared it and when it lapses."""

    level: Level
    declared_at: datetime
    expires_at: datetime
    declared_by: str
    reason: str

    def __post_init__(self) -> None:
        """Reject an incident with no duration, declarer or reason."""
        if self.expires_at <= self.declared_at:
            raise ValueError("an incident must last some time")
        if not self.declared_by.strip():
            raise ValueError("an incident must be declared by someone")
        if not self.reason.strip():
            raise ValueError("an incident must say what is wrong")


@dataclass(frozen=True)
class Posture:
    """What the agent will still do while an incident is open."""

    reads: bool
    interactive_runs: bool
    unattended_runs: bool
    approve_everything_risky: bool
    concurrency_factor: float
    declared_by: str = ""
    reason: str = ""
    until: datetime | None = None

    @classmethod
    def normal(cls) -> Posture:
        """The posture when nothing is wrong."""
        return cls(
            reads=True,
            interactive_runs=True,
            unattended_runs=True,
            approve_everything_risky=False,
            concurrency_factor=1.0,
        )


def posture_for(incident: Incident | None, *, now: datetime) -> Posture:
    """The posture to run under, given `incident` as of `now`."""
    if incident is None or now >= incident.expires_at:
        return Posture.normal()

    severe = incident.level is Level.SEVERE

    return Posture(
        reads=True,
        interactive_runs=not severe,
        unattended_runs=False,
        approve_everything_risky=True,
        concurrency_factor=0.25 if severe else 0.5,
        declared_by=incident.declared_by,
        reason=incident.reason,
        until=incident.expires_at,
    )
