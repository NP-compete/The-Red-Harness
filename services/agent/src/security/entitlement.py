"""Which agents a team has, and who among them holds a seat."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class Refusal(Enum):
    """Why an agent could not be used."""

    TEAM_NOT_LICENSED = "team-not-licensed"
    AGENT_NOT_LICENSED = "agent-not-licensed"
    NO_SEAT = "no-seat"
    NO_SEATS_LEFT = "no-seats-left"


@dataclass(frozen=True)
class Entitlements:
    """Which agents each team is licensed for, and who holds the seats."""

    agents_by_team: dict[str, tuple[str, ...]]
    seats_by_team: dict[str, int]
    seats_taken: dict[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        """Reject a team with a negative seat count."""
        if any(count < 0 for count in self.seats_by_team.values()):
            raise ValueError("a team cannot have fewer than no seats")
        for team, holders in self.seats_taken.items():
            if len(holders) > self.seats_by_team.get(team, 0):
                raise ValueError(f"{team} has more people seated than seats")


@dataclass(frozen=True)
class Decision:
    """Whether an agent may be used, and why not."""

    permitted: bool
    refusal: Refusal | None = None
    reason: str = ""


@dataclass(frozen=True)
class SeatResult:
    """Whether a seat was taken, and the entitlements after."""

    permitted: bool
    entitlements: Entitlements
    refusal: Refusal | None = None
    reason: str = ""


def may_use(
    person: str, *, team: str, agent: str, entitlements: Entitlements
) -> Decision:
    """Decide whether `person` may use `agent` on behalf of `team`."""
    licensed = entitlements.agents_by_team.get(team)
    if not licensed:
        return Decision(
            False, Refusal.TEAM_NOT_LICENSED, f"{team} has no agents licensed"
        )

    if agent not in licensed:
        return Decision(
            False, Refusal.AGENT_NOT_LICENSED, f"{team} is not licensed for {agent}"
        )

    if person not in entitlements.seats_taken.get(team, ()):
        return Decision(
            False, Refusal.NO_SEAT, f"{person} does not hold a seat in {team}"
        )

    return Decision(True)


def take_seat(person: str, *, team: str, entitlements: Entitlements) -> SeatResult:
    """Take a seat on `team` for `person`, if one is free."""
    holders = entitlements.seats_taken.get(team, ())
    if person in holders:
        return SeatResult(True, entitlements)

    seats = entitlements.seats_by_team.get(team, 0)
    if len(holders) >= seats:
        return SeatResult(
            False,
            entitlements,
            Refusal.NO_SEATS_LEFT,
            f"all {seats} seats in {team} are taken",
        )

    return SeatResult(
        True,
        replace(
            entitlements,
            seats_taken={**entitlements.seats_taken, team: (*holders, person)},
        ),
    )
