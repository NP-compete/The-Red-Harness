"""Choosing which remembered things are worth bringing to this conversation."""

from __future__ import annotations

import pytest

from agent.src.memory.recall import Candidate, recall


def candidate(key: str, keywords: tuple[str, ...], **kwargs) -> Candidate:
    defaults = {
        "text": f"something about {key}",
        "scope": "user",
        "source": "stated",
        "confidence": 0.9,
        "pinned": False,
        "words": 10,
    }
    defaults.update(kwargs)
    return Candidate(key=key, keywords=keywords, **defaults)


POOL = [
    candidate("format", ("report", "format")),
    candidate("timezone", ("meeting", "time")),
    candidate("diet", ("lunch", "food")),
]


def test_something_relevant_is_recalled():
    result = recall(POOL, about=("report",), budget_words=100)
    assert [item.key for item in result.recalled] == ["format"]


def test_something_irrelevant_is_left_behind():
    result = recall(POOL, about=("report",), budget_words=100)
    assert "diet" not in [item.key for item in result.recalled]


def test_why_each_memory_was_recalled_is_recorded():
    result = recall(POOL, about=("report",), budget_words=100)
    assert result.recalled[0].because == "report"


def test_several_relevant_memories_are_all_recalled():
    result = recall(POOL, about=("report", "meeting"), budget_words=100)
    assert len(result.recalled) == 2


def test_a_pinned_memory_is_recalled_even_when_unrelated():
    pool = [*POOL, candidate("always", ("nothing",), pinned=True)]
    result = recall(pool, about=("report",), budget_words=100)
    assert "always" in [item.key for item in result.recalled]


def test_a_pinned_memory_says_it_was_pinned():
    pool = [candidate("always", ("nothing",), pinned=True)]
    result = recall(pool, about=("report",), budget_words=100)
    assert result.recalled[0].because == "pinned"


def test_nothing_relevant_recalls_nothing():
    assert recall(POOL, about=("weather",), budget_words=100).recalled == ()


def test_a_tight_budget_keeps_the_most_confident():
    pool = [
        candidate("sure", ("report",), confidence=0.95, words=10),
        candidate("unsure", ("report",), confidence=0.4, words=10),
    ]
    result = recall(pool, about=("report",), budget_words=10)
    assert [item.key for item in result.recalled] == ["sure"]


def test_something_stated_beats_something_guessed_at_equal_confidence():
    pool = [
        candidate("guessed", ("report",), source="inferred", confidence=0.9, words=10),
        candidate("stated", ("report",), source="stated", confidence=0.9, words=10),
    ]
    result = recall(pool, about=("report",), budget_words=10)
    assert [item.key for item in result.recalled] == ["stated"]


def test_a_pinned_memory_is_kept_even_when_the_budget_is_tight():
    pool = [
        candidate("always", ("nothing",), pinned=True, words=10),
        candidate("relevant", ("report",), words=10),
    ]
    result = recall(pool, about=("report",), budget_words=10)
    assert [item.key for item in result.recalled] == ["always"]


def test_what_was_left_out_for_space_is_reported():
    pool = [
        candidate("first", ("report",), confidence=0.9, words=10),
        candidate("second", ("report",), confidence=0.5, words=10),
    ]
    result = recall(pool, about=("report",), budget_words=10)
    assert result.left_out == ("second",)


def test_nothing_is_left_out_when_everything_fits():
    assert recall(POOL, about=("report",), budget_words=100).left_out == ()


def test_how_many_words_were_used_is_reported():
    assert recall(POOL, about=("report",), budget_words=100).words == 10


def test_a_memory_larger_than_the_whole_budget_is_never_recalled():
    pool = [candidate("huge", ("report",), words=500)]
    assert recall(pool, about=("report",), budget_words=100).recalled == ()


def test_a_budget_of_nothing_is_refused():
    with pytest.raises(ValueError):
        recall(POOL, about=("report",), budget_words=0)


def test_recalling_about_nothing_is_refused():
    with pytest.raises(ValueError):
        recall(POOL, about=(), budget_words=100)


def test_a_candidate_with_no_keywords_is_refused():
    with pytest.raises(ValueError):
        candidate("x", ())
