"""Breaking a compound question into the things actually being asked."""

from __future__ import annotations

import pytest

from agent.src.knowledge.question_split import split_question


def test_a_single_question_stays_whole():
    result = split_question("what is the expense limit")
    assert [part.question for part in result.parts] == ["what is the expense limit"]


def test_a_question_joined_by_and_is_split():
    result = split_question("what is the expense limit and who approves it")
    assert [part.question for part in result.parts] == [
        "what is the expense limit",
        "who approves it",
    ]


def test_a_question_split_by_a_question_mark_is_split():
    result = split_question("what is the limit? who approves it?")
    assert len(result.parts) == 2


def test_a_question_joined_by_also_is_split():
    result = split_question("what is the limit, also who approves it")
    assert len(result.parts) == 2


def test_an_and_inside_a_phrase_does_not_split_it():
    result = split_question("where are the terms and conditions")
    assert len(result.parts) == 1


def test_each_part_carries_words_to_search_for():
    result = split_question("what is the expense limit")
    assert set(result.parts[0].keywords) >= {"expense", "limit"}


def test_filler_words_are_not_searched_for():
    result = split_question("what is the expense limit")
    assert "what" not in result.parts[0].keywords


def test_how_many_things_were_asked_is_reported():
    assert split_question("what is the limit and who approves it").count == 2


def test_a_compound_question_is_marked_as_such():
    assert split_question("what is the limit and who approves it").compound is True


def test_a_simple_question_is_not_marked_compound():
    assert split_question("what is the limit").compound is False


def test_a_part_with_nothing_to_search_for_is_dropped():
    result = split_question("what is the expense limit and please")
    assert len(result.parts) == 1


def test_whitespace_is_tidied_away():
    result = split_question("  what is the limit   and who approves it  ")
    assert result.parts[0].question == "what is the limit"


def test_too_many_parts_are_reported_rather_than_all_searched():
    asked = " and ".join(f"what about thing{n}" for n in range(10))
    assert split_question(asked).too_many is True


def test_an_ordinary_question_is_not_too_many():
    assert split_question("what is the limit and who approves it").too_many is False


def test_the_original_question_is_kept():
    asked = "what is the limit and who approves it"
    assert split_question(asked).original == asked


def test_an_empty_question_is_refused():
    with pytest.raises(ValueError):
        split_question("   ")


def test_a_question_of_only_filler_is_refused():
    with pytest.raises(ValueError):
        split_question("please and thank you")
