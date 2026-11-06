"""How long a signed-in session lasts, and when to ask again."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.session_lifetime import Session, State, check_session

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def session(**kwargs) -> Session:
    defaults = {
        "started_at": NOW - timedelta(hours=2),
        "last_seen_at": NOW - timedelta(minutes=5),
        "authenticated_at": NOW - timedelta(hours=2),
        "idle_limit": timedelta(minutes=30),
        "absolute_limit": timedelta(hours=12),
    }
    defaults.update(kwargs)
    return Session(**defaults)


def test_an_active_session_is_live():
    assert check_session(session(), now=NOW).state is State.LIVE


def test_an_active_session_may_be_used():
    assert check_session(session(), now=NOW).usable is True


def test_an_idle_session_is_closed():
    idle = session(last_seen_at=NOW - timedelta(hours=1))
    assert check_session(idle, now=NOW).state is State.IDLE_EXPIRED


def test_an_idle_session_may_not_be_used():
    idle = session(last_seen_at=NOW - timedelta(hours=1))
    assert check_session(idle, now=NOW).usable is False


def test_a_session_past_its_absolute_limit_is_closed_however_busy():
    busy = session(started_at=NOW - timedelta(hours=13), last_seen_at=NOW)
    assert check_session(busy, now=NOW).state is State.EXPIRED


def test_the_absolute_limit_outranks_an_idle_timeout():
    both = session(
        started_at=NOW - timedelta(hours=13), last_seen_at=NOW - timedelta(hours=1)
    )
    assert check_session(both, now=NOW).state is State.EXPIRED


def test_a_live_session_says_when_it_will_go_idle():
    checked = check_session(session(), now=NOW)
    assert checked.idle_at == NOW + timedelta(minutes=25)


def test_a_live_session_says_when_it_will_end_regardless():
    checked = check_session(session(), now=NOW)
    assert checked.ends_at == NOW + timedelta(hours=10)


def test_a_session_nearly_idle_is_warned_about():
    nearly = session(last_seen_at=NOW - timedelta(minutes=28))
    assert check_session(nearly, now=NOW).warn is True


def test_a_fresh_session_is_not_warned_about():
    assert check_session(session(), now=NOW).warn is False


def test_a_sensitive_action_needs_a_recent_sign_in():
    stale = session(authenticated_at=NOW - timedelta(hours=2))
    assert check_session(stale, now=NOW, sensitive=True).state is State.REAUTH_NEEDED


def test_a_sensitive_action_is_allowed_just_after_signing_in():
    fresh = session(authenticated_at=NOW - timedelta(minutes=2))
    assert check_session(fresh, now=NOW, sensitive=True).usable is True


def test_an_ordinary_action_does_not_need_a_recent_sign_in():
    stale = session(authenticated_at=NOW - timedelta(hours=2))
    assert check_session(stale, now=NOW).usable is True


def test_needing_to_sign_in_again_is_not_the_same_as_being_logged_out():
    stale = session(authenticated_at=NOW - timedelta(hours=2))
    assert check_session(stale, now=NOW, sensitive=True).session_still_valid is True


def test_an_expired_session_is_not_still_valid():
    expired = session(started_at=NOW - timedelta(hours=13))
    assert check_session(expired, now=NOW).session_still_valid is False


def test_a_session_seen_in_the_future_is_not_trusted():
    odd = session(last_seen_at=NOW + timedelta(hours=1))
    assert check_session(odd, now=NOW).usable is False


def test_an_idle_limit_longer_than_the_absolute_limit_is_refused():
    with pytest.raises(ValueError):
        Session(
            started_at=NOW,
            last_seen_at=NOW,
            authenticated_at=NOW,
            idle_limit=timedelta(hours=13),
            absolute_limit=timedelta(hours=12),
        )


def test_a_session_that_was_seen_before_it_started_is_refused():
    with pytest.raises(ValueError):
        Session(
            started_at=NOW,
            last_seen_at=NOW - timedelta(hours=1),
            authenticated_at=NOW,
            idle_limit=timedelta(minutes=30),
            absolute_limit=timedelta(hours=12),
        )
