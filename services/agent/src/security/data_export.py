"""Assembling everything the system holds about one person."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_SECRET_FIELDS = frozenset(
    {"token", "access_token", "refresh_token", "secret", "password"}
)


@dataclass(frozen=True)
class Export:
    """A subject's data, section by section."""

    subject: str
    sections: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    made_at: str = ""


def build_export(
    *, subject: str, held: dict[str, list[dict[str, Any]]], made_at: str = ""
) -> Export:
    """Build `subject`'s export out of what is `held`."""
    if not subject.strip():
        raise ValueError("an export must say who it is for")

    sections: dict[str, list[dict[str, Any]]] = {}
    for name, records in held.items():
        for record in records:
            owner = record.get("owner")
            if owner is not None and owner != subject:
                raise ValueError(f"{name} contains a record owned by somebody else")
        sections[name] = [_without_secrets(record) for record in records]

    return Export(
        subject=subject,
        sections=sections,
        counts={name: len(records) for name, records in sections.items()},
        made_at=made_at,
    )


def _without_secrets(record: dict[str, Any]) -> dict[str, Any]:
    """`record` with its secret fields dropped."""
    return {key: value for key, value in record.items() if key not in _SECRET_FIELDS}
