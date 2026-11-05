"""Tests that are allowed to be flaky, for a while (E26-T11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

QUARANTINE = Path(__file__).resolve().parent / "quarantine.yaml"


class QuarantineInvalid(RuntimeError):
    """The quarantine file cannot be trusted, so the build stops."""


@dataclass(frozen=True)
class Quarantined:
    test: str
    owner: str
    until: date
    reason: str = ""

    def expired(self, today: date) -> bool:
        return self.until < today


def read_quarantine(text: str) -> list[Quarantined]:
    """Parse the file, refusing anything that is not a full entry."""
    import yaml

    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise QuarantineInvalid("the quarantine file is not a mapping")
    entries = loaded.get("quarantined") or []
    if not isinstance(entries, list):
        raise QuarantineInvalid("`quarantined` is not a list")

    found: list[Quarantined] = []
    for one in entries:
        if not isinstance(one, dict):
            raise QuarantineInvalid(f"not an entry: {one!r}")
        missing = [field for field in ("test", "owner", "until") if not one.get(field)]
        if missing:
            raise QuarantineInvalid(
                f"{one.get('test') or one!r} is missing {', '.join(missing)}. "
                "An entry without an owner and a date is a blanket skip."
            )
        if "*" in str(one["test"]) or "::" not in str(one["test"]):
            raise QuarantineInvalid(
                f"{one['test']!r} is not one test's node id. A pattern would "
                "quarantine a directory, which is what this exists to prevent."
            )
        until = one["until"]
        if not isinstance(until, date):
            raise QuarantineInvalid(
                f"{one['test']}: `until` must be a date (YYYY-MM-DD), not {until!r}"
            )
        found.append(
            Quarantined(
                test=str(one["test"]),
                owner=str(one["owner"]),
                until=until,
                reason=str(one.get("reason") or ""),
            )
        )
    return found


def load(path: Path | None = None) -> list[Quarantined]:
    where = path or QUARANTINE
    if not where.is_file():
        return []
    return read_quarantine(where.read_text())


def expired(entries: list[Quarantined], today: date | None = None) -> list[Quarantined]:
    return [one for one in entries if one.expired(today or date.today())]


def apply_quarantine(items: list[Any], entries: list[Quarantined], today: date) -> None:
    """Mark the quarantined tests, and only those."""
    import pytest

    by_id = {one.test: one for one in entries if not one.expired(today)}
    for item in items:
        found = by_id.get(getattr(item, "nodeid", ""))
        if found is not None:
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        f"quarantined until {found.until} by {found.owner}"
                        + (f": {found.reason}" if found.reason else "")
                    )
                )
            )
