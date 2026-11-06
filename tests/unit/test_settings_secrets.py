"""Printing the settings must not print the keys."""

from __future__ import annotations

import pytest

from agent.src.settings import Settings

SECRET_FIELDS = [
    "POSTGRES_PASSWORD",
    "SSO_CLIENT_SECRET",
    "LANGFUSE_SECRET_KEY",
    "OTEL_AUTH_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS_CONTENT",
    "VLLM_API_KEY",
    "GUARDIAN_API_KEY",
    "MCP_TOKEN_ENCRYPTION_KEY",
    "MCP_TOKEN_ENCRYPTION_KEY_PREVIOUS",
]

GIVEAWAY = "correct-horse-battery-staple"


@pytest.mark.parametrize("field", SECRET_FIELDS)
def test_a_secret_is_not_in_the_printed_settings(field):
    kept = Settings(**{field: GIVEAWAY})
    assert GIVEAWAY not in repr(kept)
    assert GIVEAWAY not in str(kept)


@pytest.mark.parametrize("field", SECRET_FIELDS)
def test_the_secret_is_still_readable_by_the_code_that_needs_it(field):
    kept = Settings(**{field: GIVEAWAY})
    assert getattr(kept, field) == GIVEAWAY


def test_the_printed_settings_are_still_worth_printing():
    printed = repr(Settings())
    assert "AGENT_PORT" in printed and "ENVIRONMENT" in printed
