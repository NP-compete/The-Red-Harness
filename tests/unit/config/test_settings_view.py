"""E25. The settings half of the config surface, and what it hides."""

from __future__ import annotations

import pytest
from pydantic_settings import BaseSettings

from agent.src.agent.config.settings_view import (
    MASK,
    is_secret,
    settings_view,
    value_is_secret,
)


@pytest.mark.parametrize(
    "name",
    [
        "SSO_CLIENT_SECRET",
        "POSTGRES_PASSWORD",
        "OTEL_AUTH_TOKEN",
        "LANGFUSE_SECRET_KEY",
        "MCP_TOKEN_ENCRYPTION_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS_CONTENT",
    ],
)
def test_a_secret_name_is_masked(name):
    assert is_secret(name)


@pytest.mark.parametrize("name", ["MAX_OUTPUT_TOKENS", "ENABLE_AUTH", "AGENT_PORT"])
def test_a_harmless_name_is_not_masked(name):
    assert not is_secret(name)


@pytest.mark.parametrize(
    "name", ["MCP_RESOLVED_TOKEN_TTL_SECONDS", "CHARS_PER_TOKEN_ESTIMATE"]
)
def test_a_numeric_setting_is_shown_even_when_its_name_looks_secret(name):
    """Masking a timeout teaches people the mask means nothing."""
    assert is_secret(name), "the name rule does flag it, which is the point"
    row = next(f for f in settings_view()["fields"] if f["name"] == name)
    assert row["masked"] is False
    assert row["value"] != MASK


@pytest.mark.parametrize(
    ("value", "secret"),
    [
        ("redis://localhost:6379/0", False),
        ("redis://user:pass@host:6379/0", True),
        ("postgresql://me:hunter2@db/x", True),
        ("https://us.cloud.langfuse.com", False),
        (None, False),
        (8080, False),
    ],
)
def test_a_url_carrying_a_credential_is_masked_by_value(value, secret):
    assert value_is_secret(value) is secret


class _Example(BaseSettings):
    AGENT_PORT: int = 5002
    POSTGRES_PASSWORD: str = "hunter2"
    REDIS_URL: str = "redis://user:pass@host/0"
    ENABLE_AUTH: bool = False


def test_the_view_masks_and_says_how_many(monkeypatch):
    monkeypatch.setenv("AGENT_PORT", "9999")
    monkeypatch.delenv("REDIS_URL", raising=False)
    view = settings_view(_Example())
    by_name = {f["name"]: f for f in view["fields"]}

    assert by_name["POSTGRES_PASSWORD"]["value"] == MASK
    assert by_name["POSTGRES_PASSWORD"]["default"] == MASK
    assert by_name["REDIS_URL"]["value"] == MASK, "credential in a URL"
    assert by_name["ENABLE_AUTH"]["value"] is False, "a bool is not a number here"
    assert view["masked"] == 2
    assert view["total"] == 4


def test_from_env_is_reported_even_when_the_value_equals_the_default(monkeypatch):
    """ "Someone set this" is the useful fact, not "it differs"."""
    monkeypatch.setenv("AGENT_PORT", "5002")
    row = next(
        f for f in settings_view(_Example())["fields"] if f["name"] == "AGENT_PORT"
    )
    assert row["from_env"] is True
    assert row["overridden"] is False


def test_the_view_says_it_cannot_be_edited():
    view = settings_view(_Example())
    assert view["editable"] is False
    assert "restart" in view["why_readonly"]


def test_the_real_settings_render_without_leaking():
    """Every field marked masked must actually be masked, end to end."""
    view = settings_view()
    assert view["total"] > 100
    for field in view["fields"]:
        if field["masked"]:
            assert field["value"] == MASK, field["name"]
            assert field["default"] == MASK, field["name"]


class _Limits(BaseSettings):
    REQUEST_BODY_MAX_SIZE: int = 1_000_000
    MODEL_TIMEOUT_SECONDS: int = 30
    AGENT_NAME: str = "workpilot"


def test_an_override_that_raises_a_limit_is_named(monkeypatch):
    """The useful half of "eleven settings differ from their defaults"."""
    monkeypatch.setenv("REQUEST_BODY_MAX_SIZE", "50000000")
    monkeypatch.setenv("AGENT_NAME", "something else")
    view = settings_view(_Limits())
    assert view["loosened"] == ["REQUEST_BODY_MAX_SIZE"], (
        "a bigger number is a loosened limit; a different word is not"
    )


def test_an_override_that_tightens_is_not_named(monkeypatch):
    monkeypatch.delenv("REQUEST_BODY_MAX_SIZE", raising=False)
    monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", "5")
    loosened = settings_view(_Limits())["loosened"]
    assert "MODEL_TIMEOUT_SECONDS" not in loosened


def test_nothing_overridden_is_an_empty_list_not_an_error(monkeypatch):
    """`diff_config` refuses an empty comparison, rightly — "nothing"""
    for name in ("REQUEST_BODY_MAX_SIZE", "MODEL_TIMEOUT_SECONDS", "AGENT_NAME"):
        monkeypatch.delenv(name, raising=False)
    assert settings_view(_Limits())["loosened"] == []


def test_a_masked_field_is_not_compared(monkeypatch):
    """Both sides are the mask, so a comparison would be meaningless"""
    monkeypatch.setenv("POSTGRES_PASSWORD", "999999")
    view = settings_view(_Example())
    assert "POSTGRES_PASSWORD" not in view["loosened"]
