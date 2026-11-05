"""Looking for credentials in text that is about to leave the run."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

MIN_PASSWORD = 6
MIN_KEY = 12
PLACEHOLDERS = {"", "redacted", "none", "null", "changeme", "example"}


class Kind(Enum):
    """The kind of credential a finding looks like."""

    PRIVATE_KEY = "private-key"
    BEARER_TOKEN = "bearer-token"
    CONNECTION_STRING = "connection-string"
    PASSWORD = "password"
    API_KEY = "api-key"


_VALUE = r'(?:"([^"]*)"|\'([^\']*)\'|(\S+))'

PATTERNS: tuple[tuple[Kind, re.Pattern[str], int], ...] = (
    (Kind.PRIVATE_KEY, re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), 0),
    (Kind.BEARER_TOKEN, re.compile(r"(?i)\bbearer\s+(\S+)"), MIN_KEY),
    (
        Kind.CONNECTION_STRING,
        re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:([^\s:/@]+)@"),
        MIN_PASSWORD,
    ),
    (
        Kind.PASSWORD,
        re.compile(rf"(?i)\b(?:password|passwd|pwd|secret)\s*[=:]\s*{_VALUE}"),
        MIN_PASSWORD,
    ),
    (
        Kind.API_KEY,
        re.compile(
            rf"(?i)\b[a-z_]*(?:api[_-]?key|access[_-]?token|token)\s*[=:]\s*{_VALUE}"
        ),
        MIN_KEY,
    ),
)


@dataclass(frozen=True)
class Finding:
    """One suspected credential, masked, and where it was found."""

    kind: Kind
    line: int
    excerpt: str


@dataclass(frozen=True)
class Report:
    """What a scan found, and whether the text is safe to send."""

    findings: tuple[Finding, ...]
    safe_to_send: bool
    summary: str


def scan(text: str) -> Report:
    """Scan `text` for anything that looks like a credential."""
    findings: list[Finding] = []
    claimed: list[tuple[int, int]] = []

    for kind, pattern, minimum in PATTERNS:
        for match in pattern.finditer(text):
            value = next((group for group in match.groups() if group is not None), "")
            if minimum and not _is_secret(value, minimum):
                continue
            if any(start <= match.start() < end for start, end in claimed):
                continue
            claimed.append((match.start(), match.end()))
            findings.append(
                Finding(
                    kind=kind,
                    line=text.count("\n", 0, match.start()) + 1,
                    excerpt=_mask(match.group(0), value),
                )
            )

    findings.sort(key=lambda finding: finding.line)
    return Report(
        findings=tuple(findings),
        safe_to_send=not findings,
        summary=_summarise(findings),
    )


def _is_secret(value: str, minimum: int) -> bool:
    """Whether a matched value is plausibly a real secret."""
    if len(value) < minimum:
        return False
    if value.strip().lower() in PLACEHOLDERS:
        return False
    if value.startswith("<") or value.endswith(">"):
        return False
    return len(set(value)) > 1


def _mask(matched: str, value: str) -> str:
    """The matched text with the secret starred out."""
    return matched.replace(value, "*" * 8) if value else matched.split("\n", 1)[0]


def _summarise(findings: list[Finding]) -> str:
    """A one-line summary of what was found."""
    if not findings:
        return ""
    kinds = ", ".join(sorted({finding.kind.value for finding in findings}))
    return f"{len(findings)} possible credentials found ({kinds})"
