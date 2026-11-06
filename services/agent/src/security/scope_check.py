"""Whether an access stays inside the asker's own data."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

VISIBILITIES = {"private", "team", "org"}
ADMIN_ROLES = {"platform-admin"}


class Access(Enum):
    """The kind of access being asked for."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class Refusal(Enum):
    """Why access was refused."""

    WRONG_ORG = "wrong-org"
    WRONG_TEAM = "wrong-team"
    NOT_OWNER = "not-owner"


@dataclass(frozen=True)
class Asker:
    """Who is asking, and the org, teams and roles they bring."""

    person: str
    org: str
    teams: tuple[str, ...]
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject an asker with no person or no organisation."""
        if not self.org.strip():
            raise ValueError("an asker must belong to an organisation")
        if not self.person.strip():
            raise ValueError("an asker must be someone")


@dataclass(frozen=True)
class Record:
    """The record being reached for, and who it belongs to."""

    org: str
    owner: str
    team: str
    visibility: str

    def __post_init__(self) -> None:
        """Reject a record with an unknown visibility."""
        if self.visibility not in VISIBILITIES:
            raise ValueError(f"{self.visibility} is not a visibility")


@dataclass(frozen=True)
class Decision:
    """Whether access is permitted, and why not."""

    permitted: bool
    refusal: Refusal | None = None
    reason: str = ""


def may_access(asker: Asker, record: Record, access: Access) -> Decision:
    """Decide whether `asker` may make this `access` to `record`."""
    if asker.org != record.org:
        return Decision(False, Refusal.WRONG_ORG, "this is not available")

    owner = asker.person == record.owner

    if access in (Access.WRITE, Access.DELETE):
        if owner:
            return Decision(True)
        return Decision(False, Refusal.NOT_OWNER, "only the owner may change this")

    if owner or record.visibility == "org":
        return Decision(True)

    if record.visibility == "team":
        if record.team in asker.teams or set(asker.roles) & ADMIN_ROLES:
            return Decision(True)
        return Decision(False, Refusal.WRONG_TEAM, f"this belongs to {record.team}")

    return Decision(False, Refusal.NOT_OWNER, "this is private to its owner")
