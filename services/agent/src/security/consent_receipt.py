"""A record of what someone agreed to, and when."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """One moment a person granted or withdrew consent."""

    person: str
    purpose: str
    granted: bool
    at: datetime
    wording: str

    def __post_init__(self) -> None:
        """Reject an event missing its person, purpose, or wording."""
        if not self.person.strip():
            raise ValueError("a consent event must name a person")
        if not self.purpose.strip():
            raise ValueError("a consent event must name a purpose")
        if not self.wording.strip():
            raise ValueError("a consent event must record what was shown")


@dataclass(frozen=True)
class Receipt:
    """The tamper-evident record of one consent event."""

    receipt_id: str
    person: str
    purpose: str
    granted: bool
    at: datetime
    wording: str


def issue(event: Event, *, now: datetime) -> Receipt:
    """Issue a receipt for `event`, refusing one dated ahead of `now`."""
    if event.at > now:
        raise ValueError("a consent event cannot be dated in the future")

    fingerprint = "\x1f".join(
        [
            event.person,
            event.purpose,
            str(event.granted),
            event.at.isoformat(),
            event.wording,
        ]
    )

    return Receipt(
        receipt_id=hashlib.sha256(fingerprint.encode()).hexdigest()[:16],
        person=event.person,
        purpose=event.purpose,
        granted=event.granted,
        at=event.at,
        wording=event.wording,
    )


def current_consent(receipts: list[Receipt], *, purpose: str) -> bool:
    """Whether the latest receipt for `purpose` granted consent."""
    relevant = sorted(
        (receipt for receipt in receipts if receipt.purpose == purpose),
        key=lambda receipt: receipt.at,
    )
    return bool(relevant) and relevant[-1].granted
