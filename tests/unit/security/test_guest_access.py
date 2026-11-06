"""What someone from outside the organisation may do once invited in."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.guest_access import Guest, Want, may_guest

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)


def guest(**kwargs) -> Guest:
    defaults = {
        "person": "kai@outside.example",
        "invited_to": ("t1",),
        "expires_at": NOW + timedelta(days=7),
        "accepted": True,
        "may_write": True,
    }
    defaults.update(kwargs)
    return Guest(**defaults)


def test_a_guest_may_read_the_thread_they_were_invited_to():
    assert may_guest(guest(), want=Want("read", "t1"), now=NOW).allowed is True


def test_a_guest_may_not_read_a_thread_they_were_not_invited_to():
    assert may_guest(guest(), want=Want("read", "t2"), now=NOW).allowed is False


def test_a_guest_may_reply_where_they_were_given_a_voice():
    assert may_guest(guest(), want=Want("write", "t1"), now=NOW).allowed is True


def test_a_read_only_guest_may_not_reply():
    quiet = guest(may_write=False)
    assert may_guest(quiet, want=Want("write", "t1"), now=NOW).allowed is False


def test_a_guest_may_never_see_the_workspace_around_the_thread():
    assert may_guest(guest(), want=Want("browse", "t1"), now=NOW).allowed is False


def test_a_guest_may_never_invite_anyone_else():
    assert may_guest(guest(), want=Want("invite", "t1"), now=NOW).allowed is False


def test_a_guest_may_never_export():
    assert may_guest(guest(), want=Want("export", "t1"), now=NOW).allowed is False


def test_an_invitation_that_has_lapsed_allows_nothing():
    lapsed = guest(expires_at=NOW - timedelta(minutes=1))
    assert may_guest(lapsed, want=Want("read", "t1"), now=NOW).allowed is False


def test_a_lapsed_invitation_says_so():
    lapsed = guest(expires_at=NOW - timedelta(minutes=1))
    assert "expired" in may_guest(lapsed, want=Want("read", "t1"), now=NOW).reason


def test_an_invitation_not_yet_accepted_allows_nothing():
    pending = guest(accepted=False)
    assert may_guest(pending, want=Want("read", "t1"), now=NOW).allowed is False


def test_an_invitation_expiring_this_moment_has_expired():
    edge = guest(expires_at=NOW)
    assert may_guest(edge, want=Want("read", "t1"), now=NOW).allowed is False


def test_a_refusal_always_says_why():
    assert may_guest(guest(), want=Want("export", "t1"), now=NOW).reason


def test_an_allowed_want_needs_no_explanation():
    assert may_guest(guest(), want=Want("read", "t1"), now=NOW).reason == ""


def test_how_long_is_left_is_reported():
    decided = may_guest(guest(), want=Want("read", "t1"), now=NOW)
    assert decided.days_left == 7


def test_an_invitation_with_no_end_is_refused():
    with pytest.raises(ValueError):
        Guest(
            person="kai@outside.example",
            invited_to=("t1",),
            expires_at=None,
            accepted=True,
            may_write=True,
        )


def test_an_invitation_to_nothing_is_refused():
    with pytest.raises(ValueError):
        guest(invited_to=())


def test_a_naive_expiry_is_refused():
    with pytest.raises(ValueError):
        guest(expires_at=datetime(2026, 3, 8, 12, 0))
