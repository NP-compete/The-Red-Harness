"""PII scrubbing utilities for error responses."""

import re
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
FILEPATH_PATTERN = re.compile(r"(/[a-zA-Z0-9_\-./]+)|([A-Z]:\\[a-zA-Z0-9_\-\\./]+)")
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I
)
IP_ADDRESS_PATTERN = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")

SENSITIVE_KEYWORDS = {
    "password",
    "secret",
    "token",
    "key",
    "credential",
    "auth",
    "ssn",
    "social_security",
    "credit_card",
    "api_key",
}


def scrub_pii(text: str) -> str:
    """Remove PII patterns from text."""
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)

    def redact_path(match: re.Match) -> str:
        path = match.group(0)
        parts = path.replace("\\", "/").split("/")
        return f"[PATH]/{parts[-1]}" if parts else "[PATH_REDACTED]"

    text = FILEPATH_PATTERN.sub(redact_path, text)

    def redact_uuid(match: re.Match) -> str:
        uuid = match.group(0)
        return f"{uuid[:8]}-[REDACTED]"

    text = UUID_PATTERN.sub(redact_uuid, text)

    text = IP_ADDRESS_PATTERN.sub("[IP_REDACTED]", text)

    text = JWT_PATTERN.sub("[TOKEN_REDACTED]", text)

    return text


def scrub_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively scrub PII from dictionary values."""
    scrubbed: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()

        if any(kw in key_lower for kw in SENSITIVE_KEYWORDS):
            scrubbed[key] = "[REDACTED]"
        elif isinstance(value, str):
            scrubbed[key] = scrub_pii(value)
        elif isinstance(value, dict):
            scrubbed[key] = scrub_dict(value)
        elif isinstance(value, list):
            scrubbed[key] = [
                scrub_dict(item)
                if isinstance(item, dict)
                else scrub_pii(item)
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            scrubbed[key] = value

    return scrubbed


def scrub_error_response(detail: str, exc: Exception | None = None) -> dict[str, Any]:
    """Create a scrubbed error response."""
    scrubbed_detail = scrub_pii(detail)

    response = {
        "detail": scrubbed_detail,
        "error_type": "internal_error",
    }

    if exc:
        response["exception_type"] = type(exc).__name__

    return response
