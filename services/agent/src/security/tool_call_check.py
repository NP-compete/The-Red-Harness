"""The last look at a tool call before it is made."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Fault(Enum):
    """One thing that can be wrong with a tool call before it is made."""

    SERVER_UNTRUSTED = "server-untrusted"
    SHAPE_CHANGED = "shape-changed"
    BAD_ARGUMENTS = "bad-arguments"
    NO_CREDENTIAL = "no-credential"
    DESTINATION_BLOCKED = "destination-blocked"
    RATE_LIMITED = "rate-limited"
    TOO_MANY_AT_ONCE = "too-many-at-once"


WAITABLE = {Fault.RATE_LIMITED, Fault.TOO_MANY_AT_ONCE}

WORDS = {
    Fault.SERVER_UNTRUSTED: "the server is not the one that was trusted",
    Fault.SHAPE_CHANGED: "the tool has changed since it was approved",
    Fault.BAD_ARGUMENTS: "the arguments do not fit the tool",
    Fault.NO_CREDENTIAL: "there is no credential for this",
    Fault.DESTINATION_BLOCKED: "that destination may not be reached",
    Fault.RATE_LIMITED: "this is being called too often",
    Fault.TOO_MANY_AT_ONCE: "too many of these are already running",
}


@dataclass(frozen=True)
class Preflight:
    """Everything checked about a tool call before it is made."""

    tool: str
    server_trusted: bool
    shape_unchanged: bool
    arguments_valid: bool
    credential_available: bool
    destination_allowed: bool
    within_rate_limit: bool
    within_concurrency: bool
    argument_problem: str = ""
    shape_problem: str = ""

    def __post_init__(self) -> None:
        """Reject a preflight that reports a fault without saying what it is."""
        if not self.tool.strip():
            raise ValueError("a call must name its tool")
        if not self.arguments_valid and not self.argument_problem.strip():
            raise ValueError("bad arguments must say what is wrong with them")
        if not self.shape_unchanged and not self.shape_problem.strip():
            raise ValueError("a changed tool must say what changed about it")


@dataclass(frozen=True)
class Check:
    """Whether a call may go ahead, and what is wrong if not."""

    permitted: bool
    faults: tuple[Fault, ...]
    retryable: bool
    reason: str = ""


def check_call(call: Preflight) -> Check:
    """Decide whether `call` may be made, collecting every fault."""
    found = [
        fault
        for fault, ok in (
            (Fault.SERVER_UNTRUSTED, call.server_trusted),
            (Fault.SHAPE_CHANGED, call.shape_unchanged),
            (Fault.BAD_ARGUMENTS, call.arguments_valid),
            (Fault.NO_CREDENTIAL, call.credential_available),
            (Fault.DESTINATION_BLOCKED, call.destination_allowed),
            (Fault.RATE_LIMITED, call.within_rate_limit),
            (Fault.TOO_MANY_AT_ONCE, call.within_concurrency),
        )
        if not ok
    ]

    if not found:
        return Check(permitted=True, faults=(), retryable=False)

    notes = [WORDS[fault] for fault in found]
    if Fault.SHAPE_CHANGED in found and call.shape_problem:
        notes.append(call.shape_problem)
    if Fault.BAD_ARGUMENTS in found and call.argument_problem:
        notes.append(call.argument_problem)

    return Check(
        permitted=False,
        faults=tuple(found),
        retryable=all(fault in WAITABLE for fault in found),
        reason=f"{call.tool}: {'; '.join(notes)}",
    )
