"""Handing a conversation to somebody else."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.src.security.handoff import plan_handoff
from agent.src.security.ownership_transfer import (
    Thread,
    Transfer,
    plan_transfer,
)


@dataclass(frozen=True)
class HandedOver:
    """What was decided, and what the receiver must do next."""

    allowed: bool
    waiting: bool
    reason: str
    gains_access: list[str] = field(default_factory=list)
    readers_after: list[str] = field(default_factory=list)
    guests_dropped: list[str] = field(default_factory=list)
    audit_note: str = ""
    needs_connecting: tuple[str, ...] = ()
    already_connected: tuple[str, ...] = ()
    warning: str = ""


def hand_over(
    thread: Thread,
    *,
    transfer: Transfer,
    servers_used: list[str],
    receiver_connections: list[str],
) -> HandedOver:
    """Decide the hand-off, and say what the receiver must connect."""
    decided = plan_transfer(thread, transfer=transfer)

    if not decided.allowed:
        return HandedOver(
            allowed=False,
            waiting=decided.waiting,
            reason=decided.reason,
            gains_access=decided.gains_access,
            readers_after=decided.readers_after,
            guests_dropped=decided.guests_dropped,
            audit_note=decided.audit_note,
        )

    needed = plan_handoff(
        servers_used=servers_used,
        receiver_connections=receiver_connections,
        from_subject=thread.owner,
        to_subject=transfer.to,
    )

    return HandedOver(
        allowed=True,
        waiting=False,
        reason="",
        gains_access=decided.gains_access,
        readers_after=decided.readers_after,
        guests_dropped=decided.guests_dropped,
        audit_note=decided.audit_note,
        needs_connecting=needed.needs_connecting,
        already_connected=needed.already_connected,
        warning=needed.warning,
    )
