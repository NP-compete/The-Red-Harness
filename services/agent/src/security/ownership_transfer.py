"""Handing a thread to a new owner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Thread:
    """A thread being handed over, and who can currently see it."""

    thread: str
    owner: str
    org: str
    readers: tuple[str, ...]
    guests: tuple[str, ...]
    under_legal_hold: bool
    contains_personal_data: bool


@dataclass(frozen=True)
class Transfer:
    """Who a thread is being handed to, and whether they have accepted."""

    to: str
    to_org: str
    asked_by: str
    accepted: bool


@dataclass(frozen=True)
class Planned:
    """What the transfer would do, and who gains or loses access."""

    allowed: bool
    waiting: bool
    reason: str
    gains_access: list[str]
    readers_after: list[str]
    guests_dropped: list[str]
    audit_note: str


def plan_transfer(thread: Thread, *, transfer: Transfer) -> Planned:
    """Plan handing `thread` over under `transfer`."""
    if transfer.to == thread.owner:
        raise ValueError("this thread is already theirs")

    gains = [] if transfer.to in thread.readers else [transfer.to]
    readers_after = [*thread.readers, *gains]

    note = f"{thread.owner} handed {thread.thread} to {transfer.to}"
    if thread.contains_personal_data:
        note += ", which holds personal data"

    def outcome(allowed: bool, waiting: bool, reason: str) -> Planned:
        """A planned transfer with this verdict and reason."""
        return Planned(
            allowed=allowed,
            waiting=waiting,
            reason=reason,
            gains_access=gains,
            readers_after=readers_after,
            guests_dropped=list(thread.guests),
            audit_note=note,
        )

    if transfer.asked_by != thread.owner:
        return outcome(False, False, "only the owner can hand a thread over")
    if transfer.to_org != thread.org:
        return outcome(False, False, "a thread cannot leave the organisation")
    if thread.under_legal_hold:
        return outcome(False, False, "this thread is under legal hold")
    if not transfer.accepted:
        return outcome(False, True, "the new owner has not accepted yet")

    return outcome(True, False, "")
