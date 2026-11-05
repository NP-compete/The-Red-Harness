"""Deciding what to forget when there is too much to remember."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.memory.pruning import Remembered, prune

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def item(key: str, **kwargs) -> Remembered:
    defaults = {
        "key": key,
        "learned_at": NOW - timedelta(days=10),
        "last_used_at": NOW - timedelta(days=1),
        "uses": 5,
        "source": "stated",
        "pinned": False,
    }
    defaults.update(kwargs)
    return Remembered(key=key, **{k: v for k, v in defaults.items() if k != "key"})


def test_nothing_is_dropped_when_there_is_room():
    kept = prune([item("a"), item("b")], capacity=10, now=NOW)
    assert len(kept.kept) == 2


def test_nothing_is_dropped_at_exactly_capacity():
    assert len(prune([item("a"), item("b")], capacity=2, now=NOW).kept) == 2


def test_the_least_useful_is_dropped_first_when_over_capacity():
    useful = item("useful", uses=50, last_used_at=NOW)
    forgotten = item("forgotten", uses=1, last_used_at=NOW - timedelta(days=300))
    result = prune([useful, forgotten], capacity=1, now=NOW)
    assert [remembered.key for remembered in result.kept] == ["useful"]


def test_what_was_dropped_is_reported():
    useful = item("useful", uses=50, last_used_at=NOW)
    forgotten = item("forgotten", uses=1, last_used_at=NOW - timedelta(days=300))
    assert prune([useful, forgotten], capacity=1, now=NOW).dropped == ("forgotten",)


def test_something_used_often_beats_something_used_once():
    often = item("often", uses=20)
    once = item("once", uses=1)
    assert prune([often, once], capacity=1, now=NOW).kept[0].key == "often"


def test_something_used_recently_beats_something_used_long_ago():
    recent = item("recent", last_used_at=NOW, uses=5)
    old = item("old", last_used_at=NOW - timedelta(days=200), uses=5)
    assert prune([recent, old], capacity=1, now=NOW).kept[0].key == "recent"


def test_something_the_person_said_beats_something_inferred():
    stated = item("stated", source="stated", uses=3)
    guessed = item("guessed", source="inferred", uses=3)
    assert prune([stated, guessed], capacity=1, now=NOW).kept[0].key == "stated"


def test_a_pinned_memory_is_never_dropped():
    pinned = item("pinned", pinned=True, uses=0, last_used_at=NOW - timedelta(days=900))
    busy = item("busy", uses=100, last_used_at=NOW)
    result = prune([pinned, busy], capacity=1, now=NOW)
    assert "pinned" in [remembered.key for remembered in result.kept]


def test_pinning_everything_means_nothing_is_dropped():
    items = [item(f"m{n}", pinned=True) for n in range(5)]
    assert prune(items, capacity=1, now=NOW).dropped == ()


def test_pinning_everything_is_reported_as_over_capacity():
    items = [item(f"m{n}", pinned=True) for n in range(5)]
    assert prune(items, capacity=1, now=NOW).over_capacity is True


def test_an_ordinary_prune_is_not_over_capacity():
    assert prune([item("a"), item("b")], capacity=1, now=NOW).over_capacity is False


def test_a_memory_never_used_is_dropped_before_one_that_was():
    never = item("never", uses=0, last_used_at=None)
    used = item("used", uses=1)
    assert prune([never, used], capacity=1, now=NOW).kept[0].key == "used"


def test_the_kept_memories_come_back_in_a_stable_order():
    items = [item("b", uses=5), item("a", uses=5), item("c", uses=5)]
    kept = prune(items, capacity=3, now=NOW).kept
    assert [remembered.key for remembered in kept] == ["a", "b", "c"]


def test_a_capacity_of_nothing_is_refused():
    with pytest.raises(ValueError):
        prune([item("a")], capacity=0, now=NOW)


def test_remembering_nothing_prunes_nothing():
    assert prune([], capacity=5, now=NOW).kept == ()


def test_two_memories_with_the_same_key_are_refused():
    with pytest.raises(ValueError):
        prune([item("a"), item("a")], capacity=5, now=NOW)
