"""What may still be done while the connection is down."""

from __future__ import annotations

from dataclasses import dataclass

WARN_AFTER_SECONDS = 10

OFFLINE_OK = {"read"}
QUEUEABLE = {"send"}
PERMANENT = {"delete", "share", "export"}


@dataclass(frozen=True)
class Link:
    """The state of the connection, and what is waiting on it."""

    connected: bool
    seconds_down: int
    queued: int
    run_in_flight: bool

    def __post_init__(self) -> None:
        """Reject an outage lasting less than no time."""
        if self.seconds_down < 0:
            raise ValueError("an outage cannot have lasted less than no time")


@dataclass(frozen=True)
class Want:
    """What the person is trying to do."""

    action: str


@dataclass(frozen=True)
class Offline:
    """Whether it can be done now, queued, or not at all."""

    allowed: bool
    queue: bool
    reason: str
    queued: int
    warn: bool
    run_outcome_unknown: bool


def decide_offline(link: Link, *, want: Want) -> Offline:
    """Decide what to do with `want` given the state of the link."""
    warn = not link.connected and link.seconds_down >= WARN_AFTER_SECONDS
    unknown = not link.connected and link.run_in_flight

    def decided(allowed: bool, queue: bool, reason: str) -> Offline:
        """An outcome with this verdict and reason."""
        return Offline(
            allowed=allowed,
            queue=queue,
            reason=reason,
            queued=link.queued + (1 if queue else 0),
            warn=warn,
            run_outcome_unknown=unknown,
        )

    if link.connected:
        return decided(True, False, "")

    if want.action in OFFLINE_OK:
        return decided(True, False, "")
    if want.action in PERMANENT:
        return decided(False, False, f"{want.action} cannot wait in a queue")
    if want.action in QUEUEABLE:
        return decided(False, True, "")

    return decided(False, False, f"{want.action} needs the connection")
