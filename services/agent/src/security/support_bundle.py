"""Assembling what support needs to help, minus anything secret."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

MASK = "*" * 8
KEEP_FOR = timedelta(days=7)

SECRET_FIELD = re.compile(
    r"(?im)^(\s*[a-z0-9_.\-]*(?:key|token|secret|password|passwd|credential)[a-z0-9_.\-]*\s*[:=]\s*)(\S+)"
)


@dataclass(frozen=True)
class Section:
    """One section of a support bundle, and whether it is sensitive."""

    name: str
    content: str
    sensitive: bool

    def __post_init__(self) -> None:
        """Reject a section with no name."""
        if not self.name.strip():
            raise ValueError("a section must have a name")


@dataclass(frozen=True)
class Bundle:
    """An assembled support bundle, and when it stops being kept."""

    content: str
    sections: tuple[str, ...]
    redactions: int
    requested_by: str
    created_at: datetime
    expires_at: datetime


def build_bundle(
    sections: tuple[Section, ...],
    *,
    now: datetime,
    requested_by: str,
    exclude: tuple[str, ...] = (),
) -> Bundle:
    """Assemble a support bundle, redacting what is sensitive."""
    if not requested_by.strip():
        raise ValueError("a bundle must say who asked for it")
    if not sections:
        raise ValueError("a bundle needs something in it")

    included = [section for section in sections if section.name not in exclude]
    if not included:
        raise ValueError("every section was excluded, leaving nothing to send")

    parts: list[str] = []
    redactions = 0

    for section in included:
        content = section.content
        if section.sensitive:
            content, count = SECRET_FIELD.subn(rf"\1{MASK}", content)
            redactions += count
        parts.append(f"## {section.name}\n{content}")

    return Bundle(
        content="\n\n".join(parts),
        sections=tuple(section.name for section in included),
        redactions=redactions,
        requested_by=requested_by,
        created_at=now,
        expires_at=now + KEEP_FOR,
    )
