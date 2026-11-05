"""Recognising the machine someone is signing in from."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.device_trust import Device, Outcome, SignIn, check_device

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

KNOWN = (
    Device(
        fingerprint="abc123",
        label="work laptop",
        first_seen=NOW - timedelta(days=90),
        last_seen=NOW - timedelta(days=1),
        trusted=True,
    ),
)


def sign_in(**kwargs) -> SignIn:
    defaults = {
        "person": "ana",
        "fingerprint": "abc123",
        "at": NOW,
        "country": "GB",
        "last_country": "GB",
    }
    defaults.update(kwargs)
    return SignIn(**defaults)


def test_a_known_device_is_recognised():
    assert check_device(sign_in(), known=KNOWN).outcome is Outcome.KNOWN


def test_a_known_device_needs_no_extra_proof():
    assert check_device(sign_in(), known=KNOWN).step_up is False


def test_an_unknown_device_is_new():
    assert (
        check_device(sign_in(fingerprint="zzz"), known=KNOWN).outcome
        is Outcome.NEW_DEVICE
    )


def test_a_new_device_asks_for_extra_proof():
    assert check_device(sign_in(fingerprint="zzz"), known=KNOWN).step_up is True


def test_a_new_device_is_worth_telling_the_person_about():
    assert check_device(sign_in(fingerprint="zzz"), known=KNOWN).notify is True


def test_a_known_device_is_not_worth_a_notification():
    assert check_device(sign_in(), known=KNOWN).notify is False


def test_a_sign_in_from_a_new_country_asks_for_extra_proof():
    moved = sign_in(country="BR", last_country="GB")
    assert check_device(moved, known=KNOWN).step_up is True


def test_a_sign_in_from_a_new_country_is_reported_as_such():
    moved = sign_in(country="BR", last_country="GB")
    assert check_device(moved, known=KNOWN).outcome is Outcome.NEW_LOCATION


def test_a_new_device_outranks_a_new_country():
    both = sign_in(fingerprint="zzz", country="BR", last_country="GB")
    assert check_device(both, known=KNOWN).outcome is Outcome.NEW_DEVICE


def test_a_first_ever_sign_in_is_not_treated_as_suspicious():
    first = sign_in(fingerprint="zzz", last_country="")
    assert check_device(first, known=()).outcome is Outcome.FIRST_SIGN_IN


def test_a_first_ever_sign_in_still_asks_for_nothing_extra():
    first = sign_in(fingerprint="zzz", last_country="")
    assert check_device(first, known=()).step_up is False


def test_an_untrusted_known_device_still_asks_for_proof():
    untrusted = (
        Device(
            fingerprint="abc123",
            label="shared machine",
            first_seen=NOW - timedelta(days=1),
            last_seen=NOW,
            trusted=False,
        ),
    )
    assert check_device(sign_in(), known=untrusted).step_up is True


def test_a_device_unused_for_a_long_time_asks_for_proof_again():
    stale = (
        Device(
            fingerprint="abc123",
            label="old laptop",
            first_seen=NOW - timedelta(days=400),
            last_seen=NOW - timedelta(days=200),
            trusted=True,
        ),
    )
    assert check_device(sign_in(), known=stale).step_up is True


def test_the_device_label_is_carried_through_when_it_is_known():
    assert check_device(sign_in(), known=KNOWN).label == "work laptop"


def test_an_unknown_device_has_no_label_to_give():
    assert check_device(sign_in(fingerprint="zzz"), known=KNOWN).label == ""


def test_a_sign_in_without_a_fingerprint_is_refused():
    with pytest.raises(ValueError):
        sign_in(fingerprint=" ")


def test_a_device_last_seen_before_it_was_first_seen_is_refused():
    with pytest.raises(ValueError):
        Device(
            fingerprint="x",
            label="y",
            first_seen=NOW,
            last_seen=NOW - timedelta(days=1),
            trusted=True,
        )
