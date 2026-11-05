"""Removing secrets before anything is written down."""

from __future__ import annotations

from typing import Any

PLACEHOLDER = "[redacted]"

_SENSITIVE_FIELDS = frozenset(
    {"authorization", "password", "api_key", "apikey", "secret", "token", "cookie"}
)


def redact(text: str, *, secrets: list[str]) -> str:
    """`text` with every known secret replaced by a placeholder."""
    for secret in secrets:
        if secret.strip():
            text = text.replace(secret, PLACEHOLDER)
    return text


def safe_for_log(value: Any, *, secrets: list[str]) -> Any:
    """`value` with secrets and sensitive field values replaced."""
    if isinstance(value, str):
        return redact(value, secrets=secrets)
    if isinstance(value, dict):
        return {
            key: PLACEHOLDER
            if str(key).lower() in _SENSITIVE_FIELDS
            else safe_for_log(item, secrets=secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [safe_for_log(item, secrets=secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(safe_for_log(item, secrets=secrets) for item in value)
    return value
