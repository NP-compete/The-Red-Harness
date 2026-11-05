"""Answering who can reach what, for somebody who has to sign it off."""

from __future__ import annotations

import pytest

from agent.src.security.access_review import Grant, build_review

GRANTS = [
    Grant(subject="me@example.com", agent="support", via="group:sre", last_used_days=2),
    Grant(
        subject="me@example.com", agent="finance", via="group:sre", last_used_days=200
    ),
    Grant(
        subject="old@example.com", agent="support", via="direct", last_used_days=None
    ),
    Grant(subject="svc-pipeline", agent="support", via="service", last_used_days=1),
]


def review(**kwargs):
    defaults = {"grants": GRANTS, "stale_after_days": 90}
    defaults.update(kwargs)
    return build_review(**defaults)


def test_every_grant_is_listed():
    assert len(review().rows) == 4


def test_a_grant_says_how_it_was_obtained():
    row = next(r for r in review().rows if r.subject == "old@example.com")
    assert row.via == "direct"


def test_a_grant_nobody_has_used_is_flagged():
    row = next(r for r in review().rows if r.subject == "old@example.com")
    assert row.flagged is True


def test_a_grant_unused_for_a_long_time_is_flagged():
    row = next(r for r in review().rows if r.agent == "finance")
    assert row.flagged is True


def test_a_grant_in_regular_use_is_not_flagged():
    row = next(
        r
        for r in review().rows
        if r.agent == "support" and r.subject == "me@example.com"
    )
    assert row.flagged is False


def test_flagged_grants_come_first():
    assert review().rows[0].flagged is True


def test_a_direct_grant_is_called_out_as_worth_a_second_look():
    row = next(r for r in review().rows if r.via == "direct")
    assert "directly" in row.note.lower()


def test_a_group_grant_needs_no_note():
    row = next(
        r for r in review().rows if r.via == "group:sre" and r.agent == "support"
    )
    assert row.note == ""


def test_the_number_needing_attention_is_counted():
    assert review().needing_attention == 2


def test_service_accounts_are_counted_separately():
    assert review().service_accounts == 1


def test_an_empty_estate_reviews_cleanly():
    empty = build_review(grants=[], stale_after_days=90)
    assert empty.rows == () and empty.needing_attention == 0


@pytest.mark.parametrize("days", [0, -1])
def test_a_nonsense_staleness_window_is_refused(days):
    with pytest.raises(ValueError):
        build_review(grants=GRANTS, stale_after_days=days)
