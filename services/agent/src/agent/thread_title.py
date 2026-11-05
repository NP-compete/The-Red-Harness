"""Giving a conversation a name people can scan a list by."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

MAX_LENGTH = 48
PLACEHOLDER = "New conversation"

_POLITENESS = re.compile(
    r"^(?:(?:hi|hello|hey|please|kindly|can you|could you|would you|i'd like you to)[\s,]+)+",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_TOKEN = re.compile(r"[A-Za-z0-9]+")


class Source(Enum):
    """Where a thread's title came from."""

    FIRST_MESSAGE = "first-message"
    ATTACHMENT = "attachment"
    EXISTING = "existing"
    PLACEHOLDER = "placeholder"


@dataclass(frozen=True)
class Title:
    """A thread's title and where it came from."""

    text: str
    source: Source


def suggest_title(
    message: str,
    *,
    attachment: str = "",
    existing: str = "",
    pinned: bool = False,
    max_length: int = MAX_LENGTH,
) -> Title:
    """Suggest a title for a thread, keeping a pinned one as it is."""
    if max_length < 1:
        raise ValueError("a title needs room for something")

    if pinned and existing.strip():
        return Title(existing, Source.EXISTING)

    text = " ".join(message.split())

    if text and _looks_private(text):
        return Title(PLACEHOLDER, Source.PLACEHOLDER)

    if not text:
        if attachment.strip():
            return Title(f"About {attachment.strip()}", Source.ATTACHMENT)
        return Title(PLACEHOLDER, Source.PLACEHOLDER)

    text = _POLITENESS.sub("", text).strip() or text
    text = text[0].upper() + text[1:]

    return Title(_shorten(text, max_length), Source.FIRST_MESSAGE)


def _looks_private(text: str) -> bool:
    """Whether `text` holds something too private to use in a title."""
    if _EMAIL.search(text):
        return True
    return any(
        len(word) >= 16
        and any(c.isdigit() for c in word)
        and any(c.isalpha() for c in word)
        for word in _TOKEN.findall(text)
    )


def _shorten(text: str, limit: int) -> str:
    """`text` cut to `limit` characters on a word boundary."""
    if len(text) <= limit:
        return text

    kept: list[str] = []
    length = 0
    for word in text.split():
        if length + len(word) + (1 if kept else 0) > limit - 1:
            break
        length += len(word) + (1 if kept else 0)
        kept.append(word)

    return f"{' '.join(kept)}…" if kept else f"{text[: limit - 1]}…"
