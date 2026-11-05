"""Cutting an oversized tool result down to something a turn can hold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_ELLIPSIS = "…"


@dataclass(frozen=True)
class Trimmed:
    """A tool result after trimming, and how much was cut."""

    text: str
    trimmed: bool
    original_chars: int
    note: str = ""


def trim(
    text: str, *, max_chars: int, keep: Literal["start", "end", "both"] = "start"
) -> Trimmed:
    """Trim `text` to `max_chars`, keeping the start, end, or both."""
    if max_chars <= 0:
        raise ValueError("a result limit of nothing leaves the model nothing to read")

    original = len(text)
    if original <= max_chars:
        return Trimmed(text=text, trimmed=False, original_chars=original)

    if keep == "end":
        kept = text[-max_chars:]
    elif keep == "both":
        half = (max_chars - len(_ELLIPSIS)) // 2
        kept = f"{text[:half]}{_ELLIPSIS}{text[-half:]}"
    else:
        kept = text[:max_chars]

    return Trimmed(
        text=kept,
        trimmed=True,
        original_chars=original,
        note=f"{original - len(kept)} characters were left out of this result.",
    )
