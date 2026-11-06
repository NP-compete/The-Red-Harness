"""Whether what was found covers everything that was asked."""

from __future__ import annotations

import pytest

from agent.src.knowledge.coverage import Part, check_coverage

PARTS = (
    Part(question="what is the expense limit", keywords=("expense", "limit")),
    Part(question="who approves it", keywords=("approve", "approval")),
)

FOUND = (
    "Expenses have a limit of 500 per claim.",
    "A manager must give approval above that.",
)


def test_everything_asked_about_is_covered():
    assert check_coverage(PARTS, found=FOUND).complete is True


def test_a_part_with_nothing_found_is_reported():
    sparse = ("Expenses have a limit of 500 per claim.",)
    assert check_coverage(PARTS, found=sparse).uncovered == ("who approves it",)


def test_an_incomplete_answer_is_not_complete():
    sparse = ("Expenses have a limit of 500 per claim.",)
    assert check_coverage(PARTS, found=sparse).complete is False


def test_which_passage_covers_each_part_is_recorded():
    result = check_coverage(PARTS, found=FOUND)
    assert result.covered_by["what is the expense limit"] == (0,)


def test_a_part_covered_by_several_passages_records_them_all():
    found = ("Expenses have a limit of 500.", "The expense limit is reviewed yearly.")
    result = check_coverage(PARTS[:1], found=found)
    assert result.covered_by["what is the expense limit"] == (0, 1)


def test_a_passage_matching_none_of_the_words_does_not_cover_a_part():
    found = ("Claims are paid monthly.",)
    assert check_coverage(PARTS[:1], found=found).uncovered == (
        "what is the expense limit",
    )


def test_any_one_of_several_alternatives_is_enough():
    found = ("A manager must approve it.",)
    assert check_coverage(PARTS[1:], found=found).complete is True


def test_the_share_covered_is_reported():
    sparse = ("Expenses have a limit of 500 per claim.",)
    assert check_coverage(PARTS, found=sparse).share == 0.5


def test_nothing_found_covers_nothing():
    assert check_coverage(PARTS, found=()).share == 0.0


def test_nothing_found_is_reported_plainly():
    assert (
        check_coverage(PARTS, found=()).reason
        == "nothing was found for any part of this"
    )


def test_a_fully_covered_question_has_nothing_to_say():
    assert check_coverage(PARTS, found=FOUND).reason == ""


def test_a_partly_covered_question_names_what_is_missing():
    sparse = ("Expenses have a limit of 500 per claim.",)
    assert "who approves it" in check_coverage(PARTS, found=sparse).reason


def test_passages_covering_nothing_asked_are_counted():
    found = (*FOUND, "The office is open from nine.")
    assert check_coverage(PARTS, found=found).unused == (2,)


def test_no_passages_are_unused_when_all_are_relevant():
    assert check_coverage(PARTS, found=FOUND).unused == ()


def test_case_does_not_prevent_a_match():
    found = ("EXPENSE LIMIT is 500.",)
    assert check_coverage(PARTS[:1], found=found).complete is True


def test_asking_nothing_is_refused():
    with pytest.raises(ValueError):
        check_coverage((), found=FOUND)


def test_a_part_with_no_keywords_is_refused():
    with pytest.raises(ValueError):
        Part(question="what", keywords=())
