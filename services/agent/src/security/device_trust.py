"""Whether this sign-in looks like the person's usual machine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

STALE_AFTER = timedelta(days=90)


class Outcome(Enum):
    """What a sign-in looked like against the devices already known."""

    KNOWN = "known"
    NEW_DEVICE = "new-device"
    NEW_LOCATION = "new-location"
    FIRST_SIGN_IN = "first-sign-in"


@dataclass(frozen=True)
class Device:
    """One machine a person has signed in from before."""

    fingerprint: str
    label: str
    first_seen: datetime
    last_seen: datetime
    trusted: bool

    def __post_init__(self) -> None:
        """Reject a device last seen before it was first seen."""
        if self.last_seen < self.first_seen:
            raise ValueError("a device cannot be last seen before it was first seen")


@dataclass(frozen=True)
class SignIn:
    """One sign-in attempt, and where the last one came from."""

    person: str
    fingerprint: str
    at: datetime
    country: str
    last_country: str

    def __post_init__(self) -> None:
        """Reject a sign-in that does not identify the machine."""
        if not self.fingerprint.strip():
            raise ValueError("a sign-in must identify the machine")


@dataclass(frozen=True)
class Check:
    """What to do about a sign-in: step up, notify, or let it through."""

    outcome: Outcome
    step_up: bool
    notify: bool
    label: str = ""
    reason: str = ""


def check_device(sign_in: SignIn, *, known: tuple[Device, ...]) -> Check:
    """Judge `sign_in` against the devices already known for the person."""
    if not known and not sign_in.last_country:
        return Check(Outcome.FIRST_SIGN_IN, step_up=False, notify=False)

    device = next((d for d in known if d.fingerprint == sign_in.fingerprint), None)

    if device is None:
        return Check(
            Outcome.NEW_DEVICE,
            step_up=True,
            notify=True,
            reason="this machine has not been seen before",
        )

    if sign_in.last_country and sign_in.country != sign_in.last_country:
        return Check(
            Outcome.NEW_LOCATION,
            step_up=True,
            notify=True,
            label=device.label,
            reason=f"this sign-in is from {sign_in.country}, not {sign_in.last_country}",
        )

    unused_for_long = sign_in.at - device.last_seen > STALE_AFTER

    return Check(
        Outcome.KNOWN,
        step_up=not device.trusted or unused_for_long,
        notify=False,
        label=device.label,
    )
