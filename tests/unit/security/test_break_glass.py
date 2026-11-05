"""Emergency access: time-boxed, witnessed, and always recorded."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.break_glass import BreakGlass

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def session(**kwargs) -> BreakGlass:
    clock = {"now": NOW}
    bg = BreakGlass(now=lambda: clock["now"], **kwargs)
    bg.advance = lambda seconds: clock.__setitem__(
        "now", clock["now"] + timedelta(seconds=seconds)
    )
    return bg


def test_nothing_is_open_to_begin_with():
    assert session().active() == ()


def test_a_request_alone_grants_nothing():
    bg = session()
    bg.request(who="oncall@example.com", reason="incident 4471")
    assert bg.active() == ()


def test_approval_by_somebody_else_opens_access():
    bg = session()
    bg.request(who="oncall@example.com", reason="incident 4471")
    bg.approve(request_id=1, by="lead@example.com")
    assert bg.active() == ("oncall@example.com",)


def test_approving_your_own_request_is_refused():
    bg = session()
    bg.request(who="oncall@example.com", reason="incident 4471")
    with pytest.raises(PermissionError):
        bg.approve(request_id=1, by="oncall@example.com")


def test_a_request_without_a_reason_is_refused():
    with pytest.raises(ValueError):
        session().request(who="oncall@example.com", reason="  ")


def test_access_expires_on_its_own():
    bg = session(window_seconds=900)
    bg.request(who="oncall@example.com", reason="incident")
    bg.approve(request_id=1, by="lead@example.com")
    bg.advance(901)
    assert bg.active() == ()


def test_access_lasts_for_the_window():
    bg = session(window_seconds=900)
    bg.request(who="oncall@example.com", reason="incident")
    bg.approve(request_id=1, by="lead@example.com")
    bg.advance(899)
    assert bg.active() == ("oncall@example.com",)


def test_access_can_be_closed_early():
    bg = session()
    bg.request(who="oncall@example.com", reason="incident")
    bg.approve(request_id=1, by="lead@example.com")
    bg.close(request_id=1)
    assert bg.active() == ()


def test_every_request_is_recorded_whether_or_not_it_was_approved():
    bg = session()
    bg.request(who="a@example.com", reason="one")
    bg.request(who="b@example.com", reason="two")
    bg.approve(request_id=1, by="lead@example.com")
    assert len(bg.history()) == 2


def test_the_record_keeps_the_reason_and_the_approver():
    bg = session()
    bg.request(who="oncall@example.com", reason="incident 4471")
    bg.approve(request_id=1, by="lead@example.com")
    entry = bg.history()[0]
    assert entry.reason == "incident 4471" and entry.approved_by == "lead@example.com"


def test_an_unknown_request_cannot_be_approved():
    with pytest.raises(LookupError):
        session().approve(request_id=99, by="lead@example.com")


def test_history_cannot_be_rewritten():
    bg = session()
    bg.request(who="oncall@example.com", reason="incident")
    assert isinstance(bg.history(), tuple)
