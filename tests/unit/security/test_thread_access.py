"""Who may open a conversation, and what they may do with it."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.thread_access import Level, Thread, Viewer, access_for

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def thread(**kwargs) -> Thread:
    defaults = {
        "owner": "ana",
        "org": "acme",
        "team": "finance",
        "visibility": "private",
        "share_link": "",
        "share_expires_at": None,
        "held_by": "",
    }
    defaults.update(kwargs)
    return Thread(**defaults)


def viewer(**kwargs) -> Viewer:
    defaults = {"person": "ana", "org": "acme", "teams": ("finance",), "link": ""}
    defaults.update(kwargs)
    return Viewer(**defaults)


def test_the_owner_may_write():
    assert access_for(thread(), viewer(), now=NOW).level is Level.WRITE


def test_someone_else_in_the_team_cannot_open_a_private_thread():
    assert access_for(thread(), viewer(person="bo"), now=NOW).level is Level.NONE


def test_a_team_thread_may_be_read_by_the_team():
    shared = thread(visibility="team")
    assert access_for(shared, viewer(person="bo"), now=NOW).level is Level.READ


def test_a_team_thread_cannot_be_read_from_another_team():
    shared = thread(visibility="team")
    assert (
        access_for(shared, viewer(person="cy", teams=("legal",)), now=NOW).level
        is Level.NONE
    )


def test_nobody_from_another_organisation_may_open_it():
    shared = thread(visibility="org")
    outsider = viewer(person="dee", org="globex", teams=("finance",))
    assert access_for(shared, outsider, now=NOW).level is Level.NONE


def test_a_share_link_grants_reading():
    shared = thread(share_link="abc", share_expires_at=NOW + timedelta(days=1))
    guest = viewer(person="dee", org="globex", teams=(), link="abc")
    assert access_for(shared, guest, now=NOW).level is Level.READ


def test_a_share_link_never_grants_writing():
    shared = thread(share_link="abc", share_expires_at=NOW + timedelta(days=1))
    guest = viewer(person="dee", org="globex", teams=(), link="abc")
    assert access_for(shared, guest, now=NOW).level is not Level.WRITE


def test_an_expired_share_link_grants_nothing():
    shared = thread(share_link="abc", share_expires_at=NOW - timedelta(days=1))
    guest = viewer(person="dee", org="globex", teams=(), link="abc")
    assert access_for(shared, guest, now=NOW).level is Level.NONE


def test_a_wrong_link_grants_nothing():
    shared = thread(share_link="abc", share_expires_at=NOW + timedelta(days=1))
    guest = viewer(person="dee", org="globex", teams=(), link="wrong")
    assert access_for(shared, guest, now=NOW).level is Level.NONE


def test_a_link_does_not_lower_what_the_owner_already_has():
    shared = thread(share_link="abc", share_expires_at=NOW + timedelta(days=1))
    assert access_for(shared, viewer(link="abc"), now=NOW).level is Level.WRITE


def test_a_thread_someone_else_is_working_in_is_read_only():
    busy = thread(held_by="bo", visibility="team")
    assert access_for(busy, viewer(), now=NOW).level is Level.READ


def test_a_held_thread_says_who_is_in_it():
    busy = thread(held_by="bo")
    assert "bo" in access_for(busy, viewer(), now=NOW).reason


def test_a_thread_the_viewer_is_holding_is_writable():
    mine = thread(held_by="ana")
    assert access_for(mine, viewer(), now=NOW).level is Level.WRITE


def test_a_departed_owner_does_not_keep_the_thread_from_the_team():
    orphaned = thread(owner="gone", visibility="team")
    assert access_for(orphaned, viewer(person="bo"), now=NOW).level is Level.READ


def test_the_reason_is_given_when_nothing_is_granted():
    assert access_for(thread(), viewer(person="bo"), now=NOW).reason != ""


def test_an_unknown_visibility_is_refused():
    with pytest.raises(ValueError):
        thread(visibility="everyone")


def test_a_share_link_without_an_expiry_is_refused():
    with pytest.raises(ValueError):
        thread(share_link="abc", share_expires_at=None)
