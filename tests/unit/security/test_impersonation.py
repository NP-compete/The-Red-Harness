"""An administrator acting as someone else, and what that costs them."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.impersonation import (
    Grant,
    Refusal,
    Request,
    begin_impersonation,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def request(**kwargs) -> Request:
    defaults = {
        "administrator": "cy",
        "subject": "ana",
        "reason": "investigating a failed run reported by the user",
        "consent": Grant(
            subject="ana",
            granted_at=NOW - timedelta(minutes=5),
            expires_at=NOW + timedelta(hours=1),
        ),
        "administrator_roles": ("support",),
    }
    defaults.update(kwargs)
    return Request(**defaults)


def test_an_administrator_with_consent_may_act_as_the_subject():
    assert begin_impersonation(request(), now=NOW).permitted is True


def test_acting_without_consent_is_refused():
    assert (
        begin_impersonation(request(consent=None), now=NOW).refusal
        is Refusal.NO_CONSENT
    )


def test_acting_on_expired_consent_is_refused():
    stale = Grant(
        subject="ana",
        granted_at=NOW - timedelta(days=2),
        expires_at=NOW - timedelta(hours=1),
    )
    assert (
        begin_impersonation(request(consent=stale), now=NOW).refusal
        is Refusal.CONSENT_EXPIRED
    )


def test_consent_from_someone_else_does_not_count():
    borrowed = Grant(
        subject="bo",
        granted_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
    )
    assert (
        begin_impersonation(request(consent=borrowed), now=NOW).refusal
        is Refusal.WRONG_SUBJECT
    )


def test_an_administrator_without_the_role_is_refused():
    assert (
        begin_impersonation(request(administrator_roles=()), now=NOW).refusal
        is Refusal.NOT_PERMITTED
    )


def test_acting_as_yourself_is_refused():
    assert begin_impersonation(request(subject="cy"), now=NOW).refusal is Refusal.SELF


def test_a_session_without_a_reason_is_refused():
    assert (
        begin_impersonation(request(reason="  "), now=NOW).refusal is Refusal.NO_REASON
    )


def test_a_token_gesture_of_a_reason_is_refused():
    assert (
        begin_impersonation(request(reason="x"), now=NOW).refusal is Refusal.NO_REASON
    )


def test_the_session_ends_when_the_consent_does():
    session = begin_impersonation(request(), now=NOW)
    assert session.expires_at == NOW + timedelta(hours=1)


def test_a_long_consent_does_not_buy_an_unbounded_session():
    long = Grant(subject="ana", granted_at=NOW, expires_at=NOW + timedelta(days=30))
    session = begin_impersonation(request(consent=long), now=NOW)
    assert session.expires_at == NOW + timedelta(hours=4)


def test_the_session_acts_as_the_subject():
    assert begin_impersonation(request(), now=NOW).acting_as == "ana"


def test_the_session_never_forgets_who_is_really_there():
    assert begin_impersonation(request(), now=NOW).really == "cy"


def test_the_session_is_read_only_by_default():
    assert begin_impersonation(request(), now=NOW).read_only is True


def test_writing_may_be_asked_for_explicitly():
    session = begin_impersonation(request(), now=NOW, read_only=False)
    assert session.read_only is False


def test_an_impersonated_session_cannot_grant_further_impersonation():
    session = begin_impersonation(request(), now=NOW)
    assert session.may_impersonate is False


def test_the_reason_is_carried_into_the_session():
    assert "failed run" in begin_impersonation(request(), now=NOW).reason


def test_a_refused_session_acts_as_nobody():
    assert begin_impersonation(request(consent=None), now=NOW).acting_as == ""


def test_a_grant_that_expires_before_it_starts_is_refused():
    with pytest.raises(ValueError):
        Grant(subject="ana", granted_at=NOW, expires_at=NOW - timedelta(hours=1))


def test_a_grant_without_a_subject_is_refused():
    with pytest.raises(ValueError):
        Grant(subject=" ", granted_at=NOW, expires_at=NOW + timedelta(hours=1))
