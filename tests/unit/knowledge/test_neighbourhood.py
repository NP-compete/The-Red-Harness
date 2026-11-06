"""Giving a retrieved passage enough of its surroundings to make sense."""

from __future__ import annotations

import pytest

from agent.src.knowledge.neighbourhood import Chunk, expand

DOC = (
    Chunk(document="handbook", index=0, text="one two three", words=3),
    Chunk(document="handbook", index=1, text="four five six", words=3),
    Chunk(document="handbook", index=2, text="seven eight nine", words=3),
    Chunk(document="handbook", index=3, text="ten eleven twelve", words=3),
    Chunk(document="policy", index=0, text="other document", words=2),
)


def test_a_passage_comes_back_with_its_neighbours():
    result = expand(DOC[2], within=DOC, budget_words=20)
    assert [chunk.index for chunk in result.chunks] == [1, 2, 3]


def test_the_matched_passage_is_marked():
    assert expand(DOC[2], within=DOC, budget_words=20).matched_index == 2


def test_the_first_passage_has_nothing_before_it():
    result = expand(DOC[0], within=DOC, budget_words=20)
    assert [chunk.index for chunk in result.chunks] == [0, 1]


def test_the_last_passage_has_nothing_after_it():
    result = expand(DOC[3], within=DOC, budget_words=20)
    assert [chunk.index for chunk in result.chunks] == [2, 3]


def test_neighbours_from_another_document_are_never_included():
    result = expand(DOC[3], within=DOC, budget_words=100)
    assert all(chunk.document == "handbook" for chunk in result.chunks)


def test_a_tight_budget_keeps_only_the_match():
    result = expand(DOC[2], within=DOC, budget_words=3)
    assert [chunk.index for chunk in result.chunks] == [2]


def test_a_budget_too_small_even_for_the_match_still_returns_it():
    result = expand(DOC[2], within=DOC, budget_words=1)
    assert [chunk.index for chunk in result.chunks] == [2]


def test_a_budget_too_small_says_the_passage_stands_alone():
    assert expand(DOC[2], within=DOC, budget_words=1).trimmed is True


def test_a_comfortable_budget_is_not_trimmed():
    assert expand(DOC[2], within=DOC, budget_words=20).trimmed is False


def test_the_passage_before_is_preferred_when_only_one_fits():
    result = expand(DOC[2], within=DOC, budget_words=6)
    assert [chunk.index for chunk in result.chunks] == [1, 2]


def test_the_text_comes_back_joined_in_order():
    result = expand(DOC[1], within=DOC, budget_words=20)
    assert result.text == "one two three four five six seven eight nine"


def test_how_many_words_were_used_is_reported():
    assert expand(DOC[1], within=DOC, budget_words=20).words == 9


def test_a_passage_not_in_the_collection_is_refused():
    stray = Chunk(document="elsewhere", index=0, text="x", words=1)
    with pytest.raises(ValueError):
        expand(stray, within=DOC, budget_words=10)


def test_a_budget_of_nothing_is_refused():
    with pytest.raises(ValueError):
        expand(DOC[0], within=DOC, budget_words=0)


def test_an_empty_collection_is_refused():
    with pytest.raises(ValueError):
        expand(DOC[0], within=(), budget_words=10)


def test_a_chunk_claiming_no_words_is_refused():
    with pytest.raises(ValueError):
        Chunk(document="a", index=0, text="something", words=0)
