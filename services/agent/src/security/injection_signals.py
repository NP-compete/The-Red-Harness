"""Looking for instructions in content the agent only meant to read."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

EVIDENCE_LIMIT = 120

# Zero-width, word-joiner and bidi-override codepoints, written as escapes so
# the source file does not itself contain the characters it is looking for.
HIDDEN = re.compile("[\u200b-\u200f\u2060\u2066-\u2069\u202a-\u202e\ufeff]")


class Signal(Enum):
    """One sign that content is trying to instruct the agent."""

    OVERRIDE_ATTEMPT = "override-attempt"
    FALSE_AUTHORITY = "false-authority"
    CONCEALMENT = "concealment"
    EXFILTRATION = "exfiltration"
    HIDDEN_TEXT = "hidden-text"


PATTERNS: tuple[tuple[Signal, re.Pattern[str]], ...] = (
    (
        Signal.OVERRIDE_ATTEMPT,
        re.compile(
            r"(?is)\b(ignore|disregard|forget)\s+(?:all\s+|any\s+|your\s+|the\s+)*"
            r"(previous|prior|earlier|above|preceding)\s+(instructions|directions|rules|prompts)"
        ),
    ),
    (
        Signal.FALSE_AUTHORITY,
        re.compile(
            r"(?is)(^|\n)\s*(system|assistant|developer)\s*:"
            r"|\balready\s+been\s+approved\b"
            r"|\bapproved\s+by\s+the\s+(administrator|admin|owner|operator)\b"
        ),
    ),
    (
        Signal.CONCEALMENT,
        re.compile(
            r"(?is)\b(do\s+not|don't|never)\s+(tell|inform|mention|reveal|disclose|show)\b"
            r"[^.\n]{0,40}\b(user|human|person|operator)\b"
        ),
    ),
    (
        Signal.EXFILTRATION,
        re.compile(
            r"(?is)\b(send|post|upload|forward|exfiltrate)\b[^.\n]{0,80}"
            r"\b(to|at)\s+https?://"
        ),
    ),
    (Signal.HIDDEN_TEXT, HIDDEN),
)


@dataclass(frozen=True)
class Report:
    """What was found in a piece of content, and whether it is suspicious."""

    signals: tuple[Signal, ...]
    evidence: tuple[str, ...]
    suspicious: bool


def inspect(content: str) -> Report:
    """Inspect `content` for signs of a prompt injection."""
    signals: list[Signal] = []
    evidence: list[str] = []

    for signal, pattern in PATTERNS:
        match = pattern.search(content)
        if match is None:
            continue
        signals.append(signal)
        evidence.append(_excerpt(match.group(0)))

    return Report(
        signals=tuple(signals),
        evidence=tuple(evidence),
        suspicious=bool(signals),
    )


def _excerpt(matched: str) -> str:
    """The matched text, collapsed and trimmed for evidence."""
    collapsed = " ".join(matched.split())
    if len(collapsed) <= EVIDENCE_LIMIT:
        return collapsed
    return collapsed[:EVIDENCE_LIMIT] + "…"
