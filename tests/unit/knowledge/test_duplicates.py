"""Collapsing passages that say the same thing twice."""

from __future__ import annotations

import pytest

from agent.src.knowledge.duplicates import Passage, collapse


def passage(
    source: str, text: str, score: float = 0.5, authority: str = "reference"
) -> Passage:
    return Passage(source=source, text=text, score=score, authority=authority)


def test_different_passages_are_all_kept():
    passages = [
        passage("a", "expenses need approval"),
        passage("b", "travel is booked centrally"),
    ]
    assert len(collapse(passages).kept) == 2


def test_an_exact_copy_is_collapsed():
    passages = [
        passage("a", "expenses need approval"),
        passage("b", "expenses need approval"),
    ]
    assert len(collapse(passages).kept) == 1


def test_a_near_copy_is_collapsed():
    passages = [
        passage("a", "expenses over 500 need a manager's approval"),
        passage("b", "expenses over 500 need manager approval"),
    ]
    assert len(collapse(passages).kept) == 1


def test_a_passage_that_merely_shares_words_is_not_a_copy():
    passages = [
        passage("a", "expenses over 500 need a manager's approval"),
        passage("b", "expenses are paid monthly by the finance team"),
    ]
    assert len(collapse(passages).kept) == 2


def test_the_better_scoring_copy_is_the_one_kept():
    passages = [
        passage("a", "expenses need approval", score=0.3),
        passage("b", "expenses need approval", score=0.9),
    ]
    assert collapse(passages).kept[0].source == "b"


def test_a_more_authoritative_copy_wins_over_a_better_scoring_one():
    passages = [
        passage("notes", "expenses need approval", score=0.9, authority="note"),
        passage("policy", "expenses need approval", score=0.3, authority="policy"),
    ]
    assert collapse(passages).kept[0].source == "policy"


def test_the_sources_that_agreed_are_remembered():
    passages = [
        passage("a", "expenses need approval"),
        passage("b", "expenses need approval"),
    ]
    assert collapse(passages).kept[0].also_in == ("b",)


def test_a_unique_passage_is_not_said_to_be_elsewhere():
    assert collapse([passage("a", "unique thing")]).kept[0].also_in == ()


def test_how_many_were_collapsed_is_reported():
    passages = [
        passage("a", "expenses need approval"),
        passage("b", "expenses need approval"),
        passage("c", "expenses need approval"),
    ]
    assert collapse(passages).collapsed == 2


def test_nothing_collapsed_is_reported_as_none():
    assert collapse([passage("a", "one"), passage("b", "two")]).collapsed == 0


def test_corroboration_is_worth_knowing_about():
    passages = [
        passage("a", "expenses need approval"),
        passage("b", "expenses need approval"),
    ]
    assert collapse(passages).kept[0].corroborated is True


def test_a_lone_passage_is_not_corroborated():
    assert collapse([passage("a", "unique")]).kept[0].corroborated is False


def test_the_order_of_what_is_kept_follows_the_score():
    passages = [passage("a", "one", score=0.2), passage("b", "two", score=0.8)]
    assert [kept.source for kept in collapse(passages).kept] == ["b", "a"]


def test_an_empty_set_of_passages_is_refused():
    with pytest.raises(ValueError):
        collapse([])


def test_a_passage_with_no_text_is_refused():
    with pytest.raises(ValueError):
        passage("a", "   ")


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_an_impossible_score_is_refused(score):
    with pytest.raises(ValueError):
        passage("a", "text", score=score)
