"""PII pattern detection engine."""

import re
from dataclasses import dataclass

from agent.src.pii.config import PIIRule

BUILTIN_PATTERNS: dict[str, str] = {
    "credit_card": (
        r"\b(?:"
        r"4\d{3}(?:[-\s]?\d{4}){3}"
        r"|5[1-5]\d{2}(?:[-\s]?\d{4}){3}"
        r"|3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}"
        r"|3(?:0[0-5]|[68]\d)\d[-\s]?\d{6}[-\s]?\d{4}"
        r"|6(?:011|5\d{2})(?:[-\s]?\d{4}){3}"
        r"|(?:2131|1800)[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{3}"
        r"|35\d{2}(?:[-\s]?\d{4}){3}"
        r")\b"
    ),
    "ssn": r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    "phone": (
        r"(?<!\d)"
        r"(?:\+?1[-.\s]?)?"
        r"(?:\(?\d{3}\)?[-.\s]?)?"
        r"\d{3}[-.\s]?\d{4}"
        r"(?!\d)"
    ),
    "ip_address": r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
    "url": r"https?://[^\s<>\"'{}|\\^`\[\]]+",
    "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b",
    "address": (
        r"(?:"
        r"\b\d{1,5}\s+(?:[A-Za-z]+[\s,]+){1,4}"
        r"(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Dr(?:ive)?|Rd|Road"
        r"|Ln|Lane|Way|Ct|Court|Pl(?:ace)?|Sq(?:uare)?|Terr(?:ace)?"
        r"|Pkwy|Parkway|Hwy|Highway)\.?\b"
        r"|"
        r"\b(?:No\.?\s*)?\d{1,5}[A-Za-z]?[,\s]+(?:[A-Za-z][A-Za-z\s]{2,}[,\s]\s*){1,3}[A-Za-z]{3,}"
        r")"
    ),
}


@dataclass
class PIIMatch:
    """A single detected PII span with position, value, and rule metadata."""

    start: int
    end: int
    value: str
    rule_name: str
    label: str
    action: str


class PIIDetector:
    """Detects PII in text using compiled regex patterns."""

    def __init__(self, rules: list[PIIRule]) -> None:
        """Compile regex patterns for each rule."""
        self._patterns: list[tuple[re.Pattern[str], PIIRule, str]] = []
        for rule in rules:
            if rule.pattern_type == "builtin":
                raw = BUILTIN_PATTERNS.get(rule.name)
                if raw is None:
                    raise ValueError(
                        f"Unknown builtin PII pattern '{rule.name}'. "
                        f"Available: {list(BUILTIN_PATTERNS)}"
                    )
            else:
                if not rule.regex:
                    raise ValueError(
                        f"Custom rule '{rule.name}' must specify a 'regex' field."
                    )
                raw = rule.regex
            self._patterns.append((re.compile(raw), rule, rule.effective_label()))

    def find_all(self, text: str) -> list[PIIMatch]:
        """Return all non-overlapping PII matches ordered by position."""
        if not text:
            return []

        candidates: list[PIIMatch] = []
        for regex, rule, label in self._patterns:
            for m in regex.finditer(text):
                candidates.append(
                    PIIMatch(
                        start=m.start(),
                        end=m.end(),
                        value=m.group(),
                        rule_name=rule.name,
                        label=label,
                        action=rule.action.value,
                    )
                )

        candidates.sort(key=lambda x: (x.start, x.end))
        deduped: list[PIIMatch] = []
        last_end = -1
        for match in candidates:
            if match.start >= last_end:
                deduped.append(match)
                last_end = match.end
        return deduped
