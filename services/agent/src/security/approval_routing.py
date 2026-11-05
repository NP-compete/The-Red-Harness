"""Who to ask about a risky step, and what happens if nobody answers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

ANY = "*"
CHEAP_ENOUGH = 10.0


class OnTimeout(Enum):
    """What happens when nobody answers in time."""

    PROCEED = "proceed"
    REFUSE = "refuse"


@dataclass(frozen=True)
class Route:
    """Who approves a kind of action, how long they get, and who is next."""

    matches: str
    approvers: tuple[str, ...]
    wait: timedelta
    escalate_to: str

    def __post_init__(self) -> None:
        """Reject a route naming nobody or allowing no time to answer."""
        if not self.approvers:
            raise ValueError("a route must name someone to ask")
        if self.wait <= timedelta(0):
            raise ValueError("a route must allow some time to answer")


@dataclass(frozen=True)
class Action:
    """The action awaiting approval, and what it would cost."""

    tool: str
    target: str
    reversible: bool
    cost: float
    requested_by: str
    unattended: bool


@dataclass(frozen=True)
class Decision:
    """Who to ask, how long to wait, and what to do if nobody answers."""

    approvers: tuple[str, ...]
    wait: timedelta
    escalate_to: str
    on_timeout: OnTimeout
    ask_now: bool
    nobody_to_ask: bool
    reason: str


def route_approval(action: Action, *, routes: tuple[Route, ...]) -> Decision:
    """Work out who approves `action` under `routes`."""
    chosen = next((route for route in routes if route.matches == action.tool), None)
    if chosen is None:
        chosen = next((route for route in routes if route.matches == ANY), None)
    if chosen is None:
        raise ValueError(f"nothing says who approves {action.tool}")

    approvers = tuple(
        person for person in chosen.approvers if person != action.requested_by
    )
    nobody = not approvers

    harmless = action.reversible and action.cost < CHEAP_ENOUGH

    return Decision(
        approvers=approvers,
        wait=chosen.wait,
        escalate_to=chosen.escalate_to,
        on_timeout=OnTimeout.PROCEED if harmless and not nobody else OnTimeout.REFUSE,
        ask_now=not action.unattended,
        nobody_to_ask=nobody,
        reason=f"{action.tool} on {action.target} needs approval",
    )
