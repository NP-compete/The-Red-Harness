"""Whether what was indexed still matches where it came from."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.knowledge.freshness import Source, State, assess_freshness

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def source(**kwargs) -> Source:
    defaults = {
        "name": "handbook",
        "indexed_at": NOW - timedelta(days=2),
        "origin_changed_at": NOW - timedelta(days=5),
        "refresh_every": timedelta(days=7),
        "unreachable_since": None,
    }
    defaults.update(kwargs)
    return Source(**defaults)


def test_a_recently_indexed_source_is_current():
    assert assess_freshness(source(), now=NOW).state is State.CURRENT


def test_a_current_source_may_be_cited_without_a_caveat():
    assert assess_freshness(source(), now=NOW).caveat == ""


def test_a_source_changed_since_it_was_indexed_is_behind():
    changed = source(origin_changed_at=NOW - timedelta(hours=1))
    assert assess_freshness(changed, now=NOW).state is State.BEHIND


def test_a_source_that_is_behind_says_so_when_cited():
    changed = source(origin_changed_at=NOW - timedelta(hours=1))
    assert "changed" in assess_freshness(changed, now=NOW).caveat


def test_a_source_past_its_refresh_window_is_stale():
    old = source(
        indexed_at=NOW - timedelta(days=10), origin_changed_at=NOW - timedelta(days=20)
    )
    assert assess_freshness(old, now=NOW).state is State.STALE


def test_a_stale_source_says_how_old_it_is():
    old = source(
        indexed_at=NOW - timedelta(days=10), origin_changed_at=NOW - timedelta(days=20)
    )
    assert "10 days" in assess_freshness(old, now=NOW).caveat


def test_being_behind_matters_more_than_being_merely_old():
    both = source(
        indexed_at=NOW - timedelta(days=10), origin_changed_at=NOW - timedelta(hours=1)
    )
    assert assess_freshness(both, now=NOW).state is State.BEHIND


def test_a_source_that_cannot_be_reached_is_reported_as_such():
    lost = source(unreachable_since=NOW - timedelta(days=1))
    assert assess_freshness(lost, now=NOW).state is State.UNREACHABLE


def test_being_unreachable_matters_more_than_anything_else():
    lost = source(
        indexed_at=NOW - timedelta(days=10),
        origin_changed_at=NOW - timedelta(hours=1),
        unreachable_since=NOW - timedelta(days=1),
    )
    assert assess_freshness(lost, now=NOW).state is State.UNREACHABLE


def test_an_unreachable_source_may_still_be_cited_with_a_caveat():
    lost = source(unreachable_since=NOW - timedelta(days=1))
    result = assess_freshness(lost, now=NOW)
    assert result.citable is True and result.caveat != ""


def test_a_long_unreachable_source_should_not_be_cited():
    lost = source(unreachable_since=NOW - timedelta(days=31))
    assert assess_freshness(lost, now=NOW).citable is False


def test_when_the_next_refresh_is_due_is_reported():
    assert assess_freshness(source(), now=NOW).due_at == NOW + timedelta(days=5)


def test_a_source_with_no_refresh_schedule_is_never_stale_on_age_alone():
    never = source(
        indexed_at=NOW - timedelta(days=400),
        origin_changed_at=NOW - timedelta(days=500),
        refresh_every=None,
    )
    assert assess_freshness(never, now=NOW).state is State.CURRENT


def test_a_source_with_no_schedule_has_nothing_due():
    never = source(refresh_every=None)
    assert assess_freshness(never, now=NOW).due_at is None


def test_a_source_never_indexed_is_refused():
    with pytest.raises(ValueError):
        Source(
            name="handbook",
            indexed_at=None,
            origin_changed_at=NOW,
            refresh_every=None,
            unreachable_since=None,
        )


def test_a_source_without_a_name_is_refused():
    with pytest.raises(ValueError):
        source(name="  ")


def test_a_refresh_interval_of_nothing_is_refused():
    with pytest.raises(ValueError):
        source(refresh_every=timedelta(0))
