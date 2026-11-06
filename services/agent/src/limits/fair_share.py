"""What one person may spend, and what their team may spend together."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class OverBudget(RuntimeError):
    """A cap has been reached. Says which, and by how much."""


@dataclass(frozen=True)
class Allowance:
    """`None` for a cap means no cap."""

    per_person: Decimal | None
    per_team: Decimal | None
    teams: tuple[str, ...] = ()
    per_person_month: Decimal | None = None
    per_team_month: Decimal | None = None

    def __post_init__(self) -> None:
        """Reject a negative cap on any of the allowances."""
        for name, cap in (
            ("per_person", self.per_person),
            ("per_team", self.per_team),
            ("per_person_month", self.per_person_month),
            ("per_team_month", self.per_team_month),
        ):
            if cap is not None and cap < 0:
                raise ValueError(f"{name} is below zero, which refuses everything")

        if (
            self.per_person is not None
            and self.per_team is not None
            and self.per_team < self.per_person
        ):
            raise ValueError(
                f"per_team ({self.per_team}) is below per_person ({self.per_person}), "
                "so the personal allowance could never be spent"
            )

        if (
            self.per_person_month is not None
            and self.per_team_month is not None
            and self.per_team_month < self.per_person_month
        ):
            raise ValueError(
                f"per_team_month ({self.per_team_month}) is below "
                f"per_person_month ({self.per_person_month}), so the personal "
                "monthly allowance could never be spent"
            )


def check_within_budget(
    *,
    allowance: Allowance,
    spent_by_person: Decimal,
    spent_by_team: Decimal,
) -> None:
    """Raise unless there is room under both caps."""
    person = allowance.per_person
    if person is not None and spent_by_person >= person:
        raise OverBudget(
            f"you have spent {spent_by_person} today, which is your own "
            f"daily allowance of {person}"
        )

    team = allowance.per_team
    if team is not None and spent_by_team >= team:
        raise OverBudget(
            f"your team has spent {spent_by_team} today, which is the team's "
            f"daily allowance of {team}"
        )
