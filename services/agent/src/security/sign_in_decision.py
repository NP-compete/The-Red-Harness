"""Whether someone gets in, and what they have to prove first."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(Enum):
    """What to do about a sign-in attempt."""

    ALLOWED = "allowed"
    STEP_UP = "step-up"
    REFUSED = "refused"


@dataclass(frozen=True)
class Attempt:
    """Everything known about one sign-in attempt."""

    person: str
    network_allowed: bool
    network_exceptional: bool
    device_known: bool
    device_step_up: bool
    new_location: bool
    has_seat: bool
    account_active: bool

    def __post_init__(self) -> None:
        """Reject a sign-in by nobody."""
        if not self.person.strip():
            raise ValueError("a sign-in must be by someone")


@dataclass(frozen=True)
class Decision:
    """What the sign-in gets, and whether to notify."""

    outcome: Outcome
    step_up: bool
    read_only: bool
    exceptional: bool
    notify: bool
    reason: str = ""


def decide_sign_in(attempt: Attempt) -> Decision:
    """Decide what to do about `attempt`."""

    def refuse(reason: str) -> Decision:
        """A refusal with this reason."""
        return Decision(
            outcome=Outcome.REFUSED,
            step_up=False,
            read_only=False,
            exceptional=False,
            notify=True,
            reason=reason,
        )

    if not attempt.account_active:
        return refuse("this account is closed")

    if not attempt.network_allowed:
        return refuse("you cannot sign in from this network")

    unfamiliar = (
        not attempt.device_known or attempt.device_step_up or attempt.new_location
    )

    if unfamiliar:
        return Decision(
            outcome=Outcome.STEP_UP,
            step_up=True,
            read_only=False,
            exceptional=attempt.network_exceptional,
            notify=True,
            reason="this sign-in does not look like your usual one",
        )

    return Decision(
        outcome=Outcome.ALLOWED,
        step_up=False,
        read_only=not attempt.has_seat,
        exceptional=attempt.network_exceptional,
        notify=attempt.network_exceptional,
    )
