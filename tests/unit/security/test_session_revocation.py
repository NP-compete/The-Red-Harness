"""Cutting off sessions that should no longer work."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.session_revocation import (
    Revocation,
    Session,
    Verdict,
    check_revoked,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def session(**kwargs) -> Session:
    defaults = {
        "session_id": "s1",
        "person": "ana",
        "issued_at": NOW - timedelta(hours=1),
        "device": "laptop",
    }
    defaults.update(kwargs)
    return Session(**defaults)


def test_a_session_with_no_revocations_still_works():
    assert check_revoked(session(), revocations=(), now=NOW).verdict is Verdict.VALID


def test_a_session_revoked_by_name_stops_working():
    revocation = Revocation(
        session_id="s1", person="", issued_at=NOW, reason="asked to"
    )
    assert (
        check_revoked(session(), revocations=(revocation,), now=NOW).verdict
        is Verdict.REVOKED
    )


def test_another_session_is_untouched_by_that():
    revocation = Revocation(
        session_id="s1", person="", issued_at=NOW, reason="asked to"
    )
    other = session(session_id="s2")
    assert (
        check_revoked(other, revocations=(revocation,), now=NOW).verdict
        is Verdict.VALID
    )


def test_revoking_everything_for_a_person_catches_their_sessions():
    everywhere = Revocation(
        session_id="", person="ana", issued_at=NOW, reason="password changed"
    )
    assert (
        check_revoked(session(), revocations=(everywhere,), now=NOW).verdict
        is Verdict.REVOKED
    )


def test_revoking_everything_for_a_person_leaves_others_alone():
    everywhere = Revocation(
        session_id="", person="ana", issued_at=NOW, reason="password changed"
    )
    theirs = session(person="bo")
    assert (
        check_revoked(theirs, revocations=(everywhere,), now=NOW).verdict
        is Verdict.VALID
    )


def test_a_session_started_after_the_revocation_is_fine():
    earlier = Revocation(
        session_id="", person="ana", issued_at=NOW - timedelta(hours=2), reason="x"
    )
    assert (
        check_revoked(session(), revocations=(earlier,), now=NOW).verdict
        is Verdict.VALID
    )


def test_a_session_started_before_the_revocation_is_cut_off():
    later = Revocation(
        session_id="", person="ana", issued_at=NOW - timedelta(minutes=30), reason="x"
    )
    assert (
        check_revoked(session(), revocations=(later,), now=NOW).verdict
        is Verdict.REVOKED
    )


def test_the_reason_is_carried_back():
    revocation = Revocation(
        session_id="", person="ana", issued_at=NOW, reason="password changed"
    )
    assert (
        check_revoked(session(), revocations=(revocation,), now=NOW).reason
        == "password changed"
    )


def test_a_session_by_name_is_cut_off_whenever_it_started():
    revocation = Revocation(
        session_id="s1",
        person="",
        issued_at=NOW - timedelta(days=5),
        reason="lost laptop",
    )
    assert (
        check_revoked(session(), revocations=(revocation,), now=NOW).verdict
        is Verdict.REVOKED
    )


def test_an_expired_revocation_no_longer_applies():
    old = Revocation(
        session_id="",
        person="ana",
        issued_at=NOW - timedelta(days=100),
        reason="x",
        expires_at=NOW - timedelta(days=1),
    )
    fresh = session(issued_at=NOW - timedelta(days=200))
    assert check_revoked(fresh, revocations=(old,), now=NOW).verdict is Verdict.VALID


def test_several_revocations_are_all_considered():
    others = Revocation(session_id="s9", person="", issued_at=NOW, reason="x")
    mine = Revocation(session_id="s1", person="", issued_at=NOW, reason="mine")
    assert (
        check_revoked(session(), revocations=(others, mine), now=NOW).reason == "mine"
    )


def test_whether_the_person_must_sign_in_again_is_reported():
    revocation = Revocation(session_id="", person="ana", issued_at=NOW, reason="x")
    assert (
        check_revoked(session(), revocations=(revocation,), now=NOW).must_sign_in_again
        is True
    )


def test_a_valid_session_needs_no_fresh_sign_in():
    assert check_revoked(session(), revocations=(), now=NOW).must_sign_in_again is False


def test_a_revocation_naming_neither_a_session_nor_a_person_is_refused():
    with pytest.raises(ValueError):
        Revocation(session_id="", person="", issued_at=NOW, reason="x")


def test_a_revocation_without_a_reason_is_refused():
    with pytest.raises(ValueError):
        Revocation(session_id="s1", person="", issued_at=NOW, reason="  ")


def test_a_session_without_an_identifier_is_refused():
    with pytest.raises(ValueError):
        session(session_id=" ")
