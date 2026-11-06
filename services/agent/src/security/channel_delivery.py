"""Splitting an answer to fit a channel, and nothing else."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Channel(Protocol):
    """Somewhere a message can be delivered, and how much it takes."""

    name: str
    limit: int

    def send(self, text: str) -> None:
        """Send `text` on this channel."""
        ...


@dataclass(frozen=True)
class Delivery:
    """Whether a message went out, in how many parts, and why not."""

    sent: bool
    channel: str
    parts: int = 0
    error: str = ""


def deliver(answer: str, *, channel: Channel) -> Delivery:
    """Split an answer to the channel's limit and send each part."""
    if not answer.strip():
        return Delivery(sent=False, channel=channel.name, error="nothing to send")

    parts = [
        answer[i : i + channel.limit] for i in range(0, len(answer), channel.limit)
    ]

    for index, part in enumerate(parts):
        try:
            channel.send(part)
        except Exception as error:
            return Delivery(
                sent=False, channel=channel.name, parts=index, error=str(error)
            )

    return Delivery(sent=True, channel=channel.name, parts=len(parts))
