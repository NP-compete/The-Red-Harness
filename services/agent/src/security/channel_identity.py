"""Mapping a message from another system to the person who sent it."""

from __future__ import annotations

from dataclasses import dataclass

_KNOWN_CHANNELS = frozenset({"slack", "email", "teams", "webhook", "scm"})


@dataclass(frozen=True)
class Inbound:
    """A message arriving on a channel, and whether it was verified."""

    channel: str
    external_id: str
    verified: bool


@dataclass(frozen=True)
class Sender:
    """Who an inbound message resolved to."""

    subject: str
    channel: str


def resolve_sender(message: Inbound, *, directory: dict[str, str]) -> Sender | None:
    """Resolve `message` to a known subject, or `None`."""
    if not message.verified:
        return None
    if message.channel not in _KNOWN_CHANNELS:
        return None
    if not message.external_id.strip():
        return None

    subject = directory.get(f"{message.channel}:{message.external_id}")
    if subject is None:
        return None

    return Sender(subject=subject, channel=message.channel)
