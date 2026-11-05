"""Fitting what the model needs to know into the room available."""

from __future__ import annotations

import pytest

from agent.src.agent.context_budget import Candidate, allocate


def candidate(
    name: str, tokens: int, priority: int, required: bool = False
) -> Candidate:
    return Candidate(name=name, tokens=tokens, priority=priority, required=required)


PARTS = [
    candidate("instructions", 100, priority=0, required=True),
    candidate("history", 400, priority=1),
    candidate("retrieved", 300, priority=2),
    candidate("memories", 100, priority=3),
]


def test_everything_fits_when_there_is_room():
    result = allocate(PARTS, budget_tokens=1000)
    assert [part.name for part in result.included] == [
        "instructions",
        "history",
        "retrieved",
        "memories",
    ]


def test_nothing_is_dropped_when_everything_fits():
    assert allocate(PARTS, budget_tokens=1000).dropped == ()


def test_the_lowest_priority_is_dropped_first():
    result = allocate(PARTS, budget_tokens=850)
    assert result.dropped == ("memories",)


def test_more_is_dropped_as_the_room_shrinks():
    result = allocate(PARTS, budget_tokens=550)
    assert set(result.dropped) == {"memories", "retrieved"}


def test_what_is_required_is_never_dropped():
    result = allocate(PARTS, budget_tokens=150)
    assert "instructions" in [part.name for part in result.included]


def test_everything_optional_may_be_dropped():
    result = allocate(PARTS, budget_tokens=150)
    assert [part.name for part in result.included] == ["instructions"]


def test_a_budget_too_small_even_for_what_is_required_is_reported():
    result = allocate(PARTS, budget_tokens=50)
    assert result.over_budget is True


def test_a_budget_too_small_still_keeps_what_is_required():
    result = allocate(PARTS, budget_tokens=50)
    assert [part.name for part in result.included] == ["instructions"]


def test_a_comfortable_allocation_is_not_over_budget():
    assert allocate(PARTS, budget_tokens=1000).over_budget is False


def test_how_much_was_used_is_reported():
    assert allocate(PARTS, budget_tokens=1000).used_tokens == 900


def test_how_much_is_spare_is_reported():
    assert allocate(PARTS, budget_tokens=1000).spare_tokens == 100


def test_nothing_is_spare_when_the_budget_is_exceeded():
    assert allocate(PARTS, budget_tokens=50).spare_tokens == 0


def test_the_order_asked_for_is_preserved_in_what_is_included():
    shuffled = [PARTS[3], PARTS[0], PARTS[2], PARTS[1]]
    result = allocate(shuffled, budget_tokens=1000)
    assert [part.name for part in result.included] == [
        "memories",
        "instructions",
        "retrieved",
        "history",
    ]


def test_a_part_that_would_never_fit_is_dropped_rather_than_shrinking_others():
    parts = [candidate("huge", 5000, priority=1), candidate("small", 10, priority=2)]
    result = allocate(parts, budget_tokens=100)
    assert [part.name for part in result.included] == ["small"]


def test_two_parts_with_the_same_priority_are_refused():
    clashing = [candidate("a", 10, priority=1), candidate("b", 10, priority=1)]
    with pytest.raises(ValueError):
        allocate(clashing, budget_tokens=100)


def test_a_budget_of_nothing_is_refused():
    with pytest.raises(ValueError):
        allocate(PARTS, budget_tokens=0)


def test_a_part_with_no_tokens_is_refused():
    with pytest.raises(ValueError):
        candidate("empty", 0, priority=1)
