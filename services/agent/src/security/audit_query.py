"""Reading the record of what happened, within what the asker may see."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

WIDE_ROLES = {"auditor", "investigator"}
DETAIL_ROLES = {"investigator"}


@dataclass(frozen=True)
class Entry:
    """One entry in the audit record."""

    event: str
    person: str
    team: str
    org: str
    at: datetime
    detail: str = ""


@dataclass(frozen=True)
class Asker:
    """Who is searching the audit record, and the roles they bring."""

    person: str
    team: str
    org: str
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject an asker with no organisation."""
        if not self.org.strip():
            raise ValueError("an asker must belong to an organisation")


@dataclass(frozen=True)
class Results:
    """The entries an asker may see, and how many were held back."""

    entries: tuple[Entry, ...]
    hidden: int
    reason: str = ""


def search_audit(
    entries: tuple[Entry, ...],
    *,
    asker: Asker,
    event: str = "",
    since: datetime | None = None,
    now: datetime,
) -> Results:
    """Search the audit record, showing only what `asker` may see."""
    if since is not None and since > now:
        raise ValueError("the record does not reach into the future")

    wide = bool(set(asker.roles) & WIDE_ROLES)
    may_see_detail = bool(set(asker.roles) & DETAIL_ROLES)

    visible = [
        entry
        for entry in entries
        if entry.org == asker.org and (wide or entry.team == asker.team)
    ]

    matching = [
        entry
        for entry in visible
        if (not event or entry.event == event) and (since is None or entry.at >= since)
    ]

    shown = tuple(
        entry
        if entry.person == asker.person or may_see_detail
        else replace(entry, detail="")
        for entry in sorted(matching, key=lambda entry: entry.at, reverse=True)
    )

    return Results(
        entries=shown,
        hidden=len(entries) - len(visible),
        reason="" if shown else "nothing matched",
    )
