"""Turn a channel's payload into something the agent can run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InboundMessage:
    """A normalised request to run the agent."""

    sender: str
    text: str
    conversation: str
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AdapterError(ValueError):
    """The payload was authentic but not something we can act on."""


def _require(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise AdapterError(f"payload missing required field {key!r}")
    return payload[key]


def parse_slack(payload: dict[str, Any]) -> InboundMessage | None:
    """Parse a Slack Events API callback."""
    event = payload.get("event") or {}

    if payload.get("type") != "event_callback":
        raise AdapterError(f"unsupported Slack payload type {payload.get('type')!r}")

    if event.get("type") not in ("app_mention", "message"):
        return None

    if event.get("bot_id") or event.get("subtype"):
        return None

    text = (event.get("text") or "").strip()
    if not text:
        return None

    channel = event.get("channel") or ""
    thread_ts = event.get("thread_ts") or event.get("ts") or ""

    return InboundMessage(
        sender=str(_require(event, "user")),
        text=text,
        conversation=f"slack:{channel}:{thread_ts}",
        reply_to=channel or None,
        metadata={
            "channel": channel,
            "thread_ts": thread_ts,
            "team": payload.get("team_id", ""),
            "event_id": payload.get("event_id", ""),
        },
    )


def parse_webhook(payload: dict[str, Any]) -> InboundMessage:
    """Parse the generic webhook shape."""
    sender = str(_require(payload, "sender"))
    text = str(_require(payload, "text")).strip()
    if not text:
        raise AdapterError("text is empty")

    given = str(payload.get("conversation") or "").strip()
    conversation = f"webhook:{given or sender}"

    return InboundMessage(
        sender=sender,
        text=text,
        conversation=conversation,
        reply_to=payload.get("callback_url"),
        metadata={k: v for k, v in payload.items() if k not in ("sender", "text")},
    )


PARSERS = {"slack": parse_slack, "webhook": parse_webhook}


def parse(channel_type: str, payload: dict[str, Any]) -> InboundMessage | None:
    """Normalise a channel payload. Raises AdapterError for unknown types."""
    parser = PARSERS.get(channel_type)
    if parser is None:
        raise AdapterError(f"no parser for channel type {channel_type!r}")
    return parser(payload)
