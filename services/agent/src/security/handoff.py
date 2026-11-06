"""Moving a conversation to somebody else."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Handoff:
    """What a handover needs from the new owner, and what to warn about."""

    new_owner: str
    needs_connecting: tuple[str, ...]
    already_connected: tuple[str, ...]
    warning: str


def plan_handoff(
    *,
    servers_used: list[str],
    receiver_connections: list[str],
    from_subject: str,
    to_subject: str,
) -> Handoff:
    """Plan handing a conversation from one person to another."""
    if from_subject == to_subject:
        raise ValueError("a conversation cannot be handed to its current owner")

    used = sorted(set(servers_used))
    held = set(receiver_connections)

    missing = tuple(server for server in used if server not in held)
    present = tuple(server for server in used if server in held)

    return Handoff(
        new_owner=to_subject,
        needs_connecting=missing,
        already_connected=present,
        warning=(
            f"They will need to connect: {', '.join(missing)}." if missing else ""
        ),
    )
