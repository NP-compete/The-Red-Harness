"""What each adapter is handed, so one suite can drive all of them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Sample:
    """One adapter's view of the world."""

    channel: str
    valid: dict[str, Any]
    same_conversation: dict[str, Any]
    other_conversation: dict[str, Any]
    deliverable: dict[str, Any] | None = None

    echo: dict[str, Any] | None = None
    malformed: list[dict[str, Any]] = field(default_factory=list)
    ignored: list[dict[str, Any]] = field(default_factory=list)


def _slack_event(**over: Any) -> dict[str, Any]:
    event = {
        "type": "message",
        "user": "U123",
        "text": "what is the limit?",
        "channel": "C1",
        "ts": "1700000000.1",
        **over,
    }
    return {"type": "event_callback", "team_id": "T1", "event": event}


SLACK = Sample(
    channel="slack",
    valid=_slack_event(),
    same_conversation=_slack_event(
        text="and the other one?", ts="1700000009.9", thread_ts="1700000000.1"
    ),
    other_conversation=_slack_event(ts="1700000050.5"),
    echo=_slack_event(bot_id="B1"),
    malformed=[
        {"type": "event_callback", "event": {"type": "message", "text": "hi"}},
        {"type": "url_verification", "challenge": "x"},
    ],
    ignored=[
        _slack_event(subtype="message_changed"),
        _slack_event(subtype="channel_join"),
        _slack_event(text="   "),
    ],
)

WEBHOOK = Sample(
    channel="webhook",
    valid={"sender": "ci", "text": "deploy finished", "conversation": "run-7"},
    deliverable={
        "sender": "ci",
        "text": "deploy finished",
        "conversation": "run-7",
        "callback_url": "https://example.test/hook",
    },
    same_conversation={
        "sender": "ci",
        "text": "and the tests",
        "conversation": "run-7",
    },
    other_conversation={"sender": "ci", "text": "another", "conversation": "run-8"},
    malformed=[
        {"text": "no sender"},
        {"sender": "ci"},
        {"sender": "ci", "text": "   "},
    ],
)

EVERY_ADAPTER = [SLACK, WEBHOOK]
