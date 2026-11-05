"""A record of what someone agreed to, and when."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.consent_receipt import (
    Event,
    Receipt,
    current_consent,
    issue,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def event(**kwargs) -> Event:
    defaults = {
        "person": "ana",
        "purpose": "improve-the-system",
        "granted": True,
        "at": NOW - timedelta(days=1),
        "wording": "Allow my conversations to be studied to improve the system",
    }
    defaults.update(kwargs)
    return Event(**defaults)


def test_a_receipt_records_what_was_agreed():
    receipt = issue(event(), now=NOW)
    assert receipt.purpose == "improve-the-system"


def test_a_receipt_records_the_exact_wording_shown():
    receipt = issue(event(), now=NOW)
    assert receipt.wording.startswith("Allow my conversations")


def test_a_receipt_records_when_it_happened():
    assert issue(event(), now=NOW).at == NOW - timedelta(days=1)


def test_a_receipt_has_an_identifier():
    assert issue(event(), now=NOW).receipt_id != ""


def test_the_same_event_always_gets_the_same_identifier():
    first = issue(event(), now=NOW)
    second = issue(event(), now=NOW)
    assert first.receipt_id == second.receipt_id


def test_a_different_event_gets_a_different_identifier():
    other = issue(event(purpose="something-else"), now=NOW)
    assert other.receipt_id != issue(event(), now=NOW).receipt_id


def test_a_withdrawal_is_recorded_as_a_receipt_too():
    receipt = issue(event(granted=False), now=NOW)
    assert receipt.granted is False


def test_an_event_dated_in_the_future_is_refused():
    with pytest.raises(ValueError):
        issue(event(at=NOW + timedelta(days=1)), now=NOW)


def test_an_event_with_no_wording_is_refused():
    with pytest.raises(ValueError):
        event(wording="   ")


def test_consent_given_and_never_withdrawn_holds():
    assert (
        current_consent([issue(event(), now=NOW)], purpose="improve-the-system") is True
    )


def test_consent_withdrawn_afterwards_does_not_hold():
    given = issue(event(at=NOW - timedelta(days=2)), now=NOW)
    taken = issue(event(granted=False, at=NOW - timedelta(days=1)), now=NOW)
    assert current_consent([given, taken], purpose="improve-the-system") is False


def test_the_most_recent_event_decides():
    taken = issue(event(granted=False, at=NOW - timedelta(days=2)), now=NOW)
    given = issue(event(at=NOW - timedelta(days=1)), now=NOW)
    assert current_consent([taken, given], purpose="improve-the-system") is True


def test_the_order_receipts_are_given_in_does_not_matter():
    given = issue(event(at=NOW - timedelta(days=1)), now=NOW)
    taken = issue(event(granted=False, at=NOW - timedelta(days=2)), now=NOW)
    assert current_consent([given, taken], purpose="improve-the-system") is True


def test_consent_for_one_purpose_says_nothing_about_another():
    given = issue(event(purpose="improve-the-system"), now=NOW)
    assert current_consent([given], purpose="share-with-partners") is False


def test_no_receipts_at_all_means_no_consent():
    assert current_consent([], purpose="improve-the-system") is False


def test_a_receipt_cannot_be_altered_after_the_fact():
    receipt = issue(event(), now=NOW)
    with pytest.raises(Exception):
        receipt.granted = False  # type: ignore[misc]


def test_a_receipt_is_a_record_not_a_decision():
    assert not hasattr(Receipt, "revoke")
