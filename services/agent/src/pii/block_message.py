"""What to say when a question is refused for the data it contains."""

from __future__ import annotations

from typing import Any, Iterable

_MAX_QUOTE_CHARS = 40
_MAX_QUOTES = 5


def _quoted(text: str, matches: Iterable[Any]) -> list[str]:
    seen: list[str] = []
    for match in matches:
        start, end = getattr(match, "start", 0), getattr(match, "end", 0)
        if not 0 <= start < end <= len(text):
            continue
        found = text[start:end].strip()
        if not found:
            continue
        if len(found) > _MAX_QUOTE_CHARS:
            found = found[:_MAX_QUOTE_CHARS].rstrip() + "…"
        if found not in seen:
            seen.append(found)
        if len(seen) == _MAX_QUOTES:
            break
    return seen


def blocked_reply(text: str, matches: Iterable[Any]) -> str:
    """The refusal, naming both the kind of data and the words found."""
    matches = list(matches)
    labels = ", ".join(
        sorted(
            {str(getattr(m, "label", "")) for m in matches if getattr(m, "label", "")}
        )
    )
    quotes = _quoted(text, matches)

    said = (
        f"I'm unable to process this request as it contains sensitive "
        f"information ({labels}) that is restricted by the PII policy."
        if labels
        else "I'm unable to process this request under the PII policy."
    )
    if quotes:
        listed = ", ".join(f'"{q}"' for q in quotes)
        said += f" The part that matched: {listed}."
    return said + " Please remove the sensitive data and try again."
