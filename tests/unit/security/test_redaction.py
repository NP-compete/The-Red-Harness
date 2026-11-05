"""Keeping secrets out of the places a decision gets written down."""

from __future__ import annotations

import pytest

from agent.src.security.redaction import redact, safe_for_log

SECRETS = ["sk-live-abcdef123456", "ghp_0123456789abcdef"]


def test_text_without_a_secret_is_untouched():
    assert redact("nothing to hide here", secrets=SECRETS) == "nothing to hide here"


def test_a_known_secret_is_replaced():
    assert "sk-live" not in redact("token is sk-live-abcdef123456", secrets=SECRETS)


def test_the_replacement_says_something_was_removed():
    assert "redacted" in redact("sk-live-abcdef123456", secrets=SECRETS).lower()


def test_every_occurrence_is_replaced():
    text = "sk-live-abcdef123456 and again sk-live-abcdef123456"
    assert "sk-live" not in redact(text, secrets=SECRETS)


def test_more_than_one_secret_is_handled():
    text = "sk-live-abcdef123456 ghp_0123456789abcdef"
    cleaned = redact(text, secrets=SECRETS)
    assert "sk-live" not in cleaned and "ghp_" not in cleaned


def test_an_empty_secret_is_ignored_rather_than_redacting_everything():
    assert redact("perfectly fine", secrets=["", "   "]) == "perfectly fine"


def test_nested_values_are_cleaned():
    payload = {"headers": {"authorization": "Bearer sk-live-abcdef123456"}, "n": 3}
    cleaned = safe_for_log(payload, secrets=SECRETS)
    assert "sk-live" not in str(cleaned)


def test_structure_survives_cleaning():
    payload = {"a": ["one", {"b": "two"}], "n": 3}
    assert safe_for_log(payload, secrets=SECRETS) == payload


def test_an_authorization_header_is_dropped_even_when_the_value_is_unknown():
    payload = {"headers": {"Authorization": "Bearer something-we-never-saw"}}
    cleaned = safe_for_log(payload, secrets=[])
    assert "something-we-never-saw" not in str(cleaned)


def test_a_field_that_merely_mentions_a_token_is_kept():
    payload = {"message": "the token store was unreachable"}
    assert safe_for_log(payload, secrets=[]) == payload


@pytest.mark.parametrize("field", ["password", "api_key", "secret"])
def test_obviously_named_fields_are_dropped(field):
    cleaned = safe_for_log({field: "whatever-it-was"}, secrets=[])
    assert "whatever-it-was" not in str(cleaned)
