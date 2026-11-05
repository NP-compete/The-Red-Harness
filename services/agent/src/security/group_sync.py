"""Turning reported directory groups into the teams and roles a person holds."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MAX_AGE = timedelta(hours=24)


@dataclass(frozen=True)
class Mapping:
    """Which directory groups confer which teams and roles."""

    teams_by_group: dict[str, str]
    roles_by_group: dict[str, str]

    def __post_init__(self) -> None:
        """Reject a group mapped to both a team and a role."""
        overlap = set(self.teams_by_group) & set(self.roles_by_group)
        if overlap:
            raise ValueError(
                f"groups map to both a team and a role: {', '.join(sorted(overlap))}"
            )


@dataclass(frozen=True)
class Snapshot:
    """A person's directory groups at a moment, and what they hold now."""

    person: str
    groups: tuple[str, ...]
    taken_at: datetime
    current_teams: tuple[str, ...]
    current_roles: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a snapshot that names no person."""
        if not self.person.strip():
            raise ValueError("a snapshot must name a person")


@dataclass(frozen=True)
class Reconciliation:
    """The teams and roles a person should hold, and what changed."""

    person: str
    teams: tuple[str, ...]
    roles: tuple[str, ...]
    unmapped: tuple[str, ...]
    changed: bool
    removed_all: bool
    reason: str = ""


def reconcile(snapshot: Snapshot, mapping: Mapping, *, now: datetime) -> Reconciliation:
    """Work out a person's teams and roles from `snapshot` under `mapping`."""
    age = now - snapshot.taken_at

    if age > MAX_AGE or age < timedelta(0):
        return Reconciliation(
            person=snapshot.person,
            teams=snapshot.current_teams,
            roles=snapshot.current_roles,
            unmapped=(),
            changed=False,
            removed_all=False,
            reason="this view of the directory is stale, so nothing was changed",
        )

    teams = tuple(
        sorted(
            {
                mapping.teams_by_group[g]
                for g in snapshot.groups
                if g in mapping.teams_by_group
            }
        )
    )
    roles = tuple(
        sorted(
            {
                mapping.roles_by_group[g]
                for g in snapshot.groups
                if g in mapping.roles_by_group
            }
        )
    )
    unmapped = tuple(
        sorted(
            group
            for group in snapshot.groups
            if group not in mapping.teams_by_group
            and group not in mapping.roles_by_group
        )
    )

    changed = set(teams) != set(snapshot.current_teams) or set(roles) != set(
        snapshot.current_roles
    )

    return Reconciliation(
        person=snapshot.person,
        teams=teams,
        roles=roles,
        unmapped=unmapped,
        changed=changed,
        removed_all=bool(snapshot.current_teams) and not teams,
    )
