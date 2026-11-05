"""Marking exported content so a copy can be traced back."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

FORMATS = {"markdown", "text", "json", "csv"}
CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}
UNMARKABLE = {"json", "csv"}


class Placement(Enum):
    """Where a marking goes in an export, if anywhere."""

    FOOTER = "footer"
    NONE = "none"


@dataclass(frozen=True)
class Export:
    """The content being exported, and who is taking it."""

    content: str
    format: str
    person: str
    org: str
    classification: str

    def __post_init__(self) -> None:
        """Reject an empty export, or an unknown format or classification."""
        if not self.content.strip():
            raise ValueError("there is nothing to export")
        if self.format not in FORMATS:
            raise ValueError(f"{self.format} is not a format this can mark")
        if self.classification not in CLASSIFICATIONS:
            raise ValueError(f"{self.classification} is not a classification")


@dataclass(frozen=True)
class Marked:
    """The export after marking, and how it was marked."""

    content: str
    marked: bool
    placement: Placement
    export_id: str
    exported_by: str


def mark_export(export: Export, *, now: datetime) -> Marked:
    """Mark `export` for its classification as of `now`."""
    export_id = secrets.token_hex(6)

    def unmarked() -> Marked:
        """The export left as it is."""
        return Marked(
            content=export.content,
            marked=False,
            placement=Placement.NONE,
            export_id=export_id,
            exported_by=export.person,
        )

    if export.classification == "public" or export.format in UNMARKABLE:
        return unmarked()

    day = now.date().isoformat()
    note = f"{export.org} {export.classification} — exported {day} — {export_id}"
    body = f"<!-- {note} -->" if export.format == "markdown" else note

    return Marked(
        content=f"{export.content.rstrip()}\n\n{body}\n",
        marked=True,
        placement=Placement.FOOTER,
        export_id=export_id,
        exported_by=export.person,
    )
