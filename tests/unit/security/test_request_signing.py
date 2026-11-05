"""Signing what the agent sends out so the receiver can trust it."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.request_signing import (
    SigningKey,
    sign_request,
    verify_signed,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

KEY = SigningKey(id="k1", secret="a-long-enough-signing-secret")


def test_a_signed_request_carries_a_signature():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    assert signed.signature != ""


def test_a_signed_request_names_the_key_used():
    assert sign_request(b"payload", key=KEY, now=NOW).key_id == "k1"


def test_a_signed_request_carries_the_time_it_was_signed():
    assert sign_request(b"payload", key=KEY, now=NOW).signed_at == NOW


def test_a_signed_request_never_carries_the_secret():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    assert KEY.secret not in signed.signature
    assert not hasattr(signed, "secret")


def test_the_same_body_at_the_same_time_signs_the_same_way():
    first = sign_request(b"payload", key=KEY, now=NOW)
    second = sign_request(b"payload", key=KEY, now=NOW)
    assert first.signature == second.signature


def test_a_different_body_signs_differently():
    first = sign_request(b"payload", key=KEY, now=NOW)
    second = sign_request(b"other", key=KEY, now=NOW)
    assert first.signature != second.signature


def test_the_same_body_at_a_different_time_signs_differently():
    first = sign_request(b"payload", key=KEY, now=NOW)
    second = sign_request(b"payload", key=KEY, now=NOW + timedelta(seconds=1))
    assert first.signature != second.signature


def test_a_freshly_signed_request_verifies():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    assert verify_signed(b"payload", signed, key=KEY, now=NOW).verified is True


def test_a_tampered_body_does_not_verify():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    assert verify_signed(b"tampered", signed, key=KEY, now=NOW).verified is False


def test_a_tampered_timestamp_does_not_verify():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    moved = type(signed)(**{**signed.__dict__, "signed_at": NOW + timedelta(seconds=5)})
    assert verify_signed(b"payload", moved, key=KEY, now=NOW).verified is False


def test_a_request_signed_with_another_key_does_not_verify():
    other = SigningKey(id="k1", secret="a-different-signing-secret")
    signed = sign_request(b"payload", key=other, now=NOW)
    assert verify_signed(b"payload", signed, key=KEY, now=NOW).verified is False


def test_a_request_older_than_the_window_does_not_verify():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    late = NOW + timedelta(minutes=10)
    assert verify_signed(b"payload", signed, key=KEY, now=late).verified is False


def test_an_expired_request_says_it_was_too_old():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    late = NOW + timedelta(minutes=10)
    assert "old" in verify_signed(b"payload", signed, key=KEY, now=late).reason


def test_a_request_from_the_future_does_not_verify():
    signed = sign_request(b"payload", key=KEY, now=NOW + timedelta(minutes=10))
    assert verify_signed(b"payload", signed, key=KEY, now=NOW).verified is False


def test_a_little_clock_drift_is_tolerated():
    signed = sign_request(b"payload", key=KEY, now=NOW + timedelta(seconds=20))
    assert verify_signed(b"payload", signed, key=KEY, now=NOW).verified is True


def test_a_failure_does_not_say_which_part_was_wrong():
    signed = sign_request(b"payload", key=KEY, now=NOW)
    reason = verify_signed(b"tampered", signed, key=KEY, now=NOW).reason
    assert "body" not in reason and "timestamp" not in reason


def test_a_short_secret_is_refused():
    with pytest.raises(ValueError):
        SigningKey(id="k1", secret="short")


def test_a_key_without_an_identifier_is_refused():
    with pytest.raises(ValueError):
        SigningKey(id=" ", secret="a-long-enough-signing-secret")
