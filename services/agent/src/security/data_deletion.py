"""Working out what removing one person's data would take with it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_AUDIT_NOTE = (
    "The audit trail is retained: it records what was done, which a deletion "
    "request cannot erase without erasing the record of the request itself."
)


@dataclass(frozen=True)
class Deletion:
    """What deleting a subject's data would remove, keep and retain."""

    subject: str
    delete: dict[str, list[str]] = field(default_factory=dict)
    kept: dict[str, list[str]] = field(default_factory=dict)
    retained: dict[str, list[str]] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def plan_deletion(*, subject: str, held: dict[str, list[dict[str, Any]]]) -> Deletion:
    """Plan deleting `subject`'s data out of what is `held`."""
    if not subject.strip():
        raise ValueError("a deletion must say who it is for")

    delete: dict[str, list[str]] = {}
    kept: dict[str, list[str]] = {}
    retained: dict[str, list[str]] = {}

    for section, records in held.items():
        if section == "audit":
            retained[section] = [r["id"] for r in records]
            continue

        mine = [r for r in records if r.get("owner") == subject]
        delete[section] = [r["id"] for r in mine if r.get("scope", "user") != "team"]
        kept[section] = [r["id"] for r in mine if r.get("scope", "user") == "team"]

    return Deletion(
        subject=subject,
        delete=delete,
        kept=kept,
        retained=retained,
        counts={section: len(ids) for section, ids in delete.items()},
        notes=[_AUDIT_NOTE] if retained else [],
    )
