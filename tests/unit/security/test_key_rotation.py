"""Replacing a signing key without breaking what is already in flight."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.key_rotation import Key, Keyring, Status, verify_with

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

CURRENT = Key(id="k2", secret="new-secret-value", retired_at=None, compromised=False)
PREVIOUS = Key(
    id="k1",
    secret="old-secret-value",
    retired_at=NOW + timedelta(hours=1),
    compromised=False,
)

KEYRING = Keyring(current=CURRENT, previous=(PREVIOUS,))


def signature(secret: str, body: bytes = b"payload") -> str:
    import hashlib
    import hmac

    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_the_current_key_verifies():
    result = verify_with(KEYRING, b"payload", signature(CURRENT.secret), now=NOW)
    assert result.status is Status.VERIFIED


def test_the_current_key_is_named():
    result = verify_with(KEYRING, b"payload", signature(CURRENT.secret), now=NOW)
    assert result.key_id == "k2"


def test_a_key_still_inside_its_overlap_verifies():
    result = verify_with(KEYRING, b"payload", signature(PREVIOUS.secret), now=NOW)
    assert result.status is Status.VERIFIED_WITH_OLD_KEY


def test_an_old_key_that_worked_says_a_rotation_is_pending():
    result = verify_with(KEYRING, b"payload", signature(PREVIOUS.secret), now=NOW)
    assert "rotate" in result.reason


def test_a_key_past_its_overlap_does_not_verify():
    late = NOW + timedelta(hours=2)
    result = verify_with(KEYRING, b"payload", signature(PREVIOUS.secret), now=late)
    assert result.status is Status.NOT_VERIFIED


def test_a_compromised_key_never_verifies_however_recent():
    burned = Keyring(
        current=CURRENT,
        previous=(
            Key(id="k1", secret="old-secret-value", retired_at=None, compromised=True),
        ),
    )
    result = verify_with(burned, b"payload", signature("old-secret-value"), now=NOW)
    assert result.status is Status.NOT_VERIFIED


def test_a_compromised_key_says_it_was_withdrawn():
    burned = Keyring(
        current=CURRENT,
        previous=(
            Key(id="k1", secret="old-secret-value", retired_at=None, compromised=True),
        ),
    )
    result = verify_with(burned, b"payload", signature("old-secret-value"), now=NOW)
    assert "withdrawn" in result.reason


def test_a_compromised_current_key_stops_everything():
    burned = Keyring(
        current=Key(
            id="k2", secret="new-secret-value", retired_at=None, compromised=True
        ),
        previous=(),
    )
    result = verify_with(burned, b"payload", signature("new-secret-value"), now=NOW)
    assert result.status is Status.NOT_VERIFIED


def test_a_wrong_signature_does_not_verify():
    result = verify_with(KEYRING, b"payload", signature("some-other-secret"), now=NOW)
    assert result.status is Status.NOT_VERIFIED


def test_a_changed_body_does_not_verify():
    result = verify_with(KEYRING, b"tampered", signature(CURRENT.secret), now=NOW)
    assert result.status is Status.NOT_VERIFIED


def test_a_malformed_signature_does_not_verify():
    assert (
        verify_with(KEYRING, b"payload", "not-hex", now=NOW).status
        is Status.NOT_VERIFIED
    )


def test_an_empty_signature_does_not_verify():
    assert verify_with(KEYRING, b"payload", "", now=NOW).status is Status.NOT_VERIFIED


def test_a_failure_never_names_which_key_was_tried():
    result = verify_with(KEYRING, b"payload", signature("some-other-secret"), now=NOW)
    assert result.key_id == ""


def test_a_keyring_with_the_same_key_twice_is_refused():
    with pytest.raises(ValueError):
        Keyring(current=CURRENT, previous=(CURRENT,))


def test_a_key_with_no_secret_is_refused():
    with pytest.raises(ValueError):
        Key(id="k3", secret="", retired_at=None, compromised=False)


def test_a_key_with_no_identifier_is_refused():
    with pytest.raises(ValueError):
        Key(id=" ", secret="something", retired_at=None, compromised=False)
