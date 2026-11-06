"""Choosing the passage to show as evidence for a claim."""

from __future__ import annotations

import pytest

from agent.src.knowledge.quote_selection import Passage, choose_quote


def passage(text: str) -> Passage:
    return Passage(source="handbook", text=text)


def test_the_sentence_carrying_the_claim_is_chosen():
    body = passage(
        "Expenses are reviewed monthly. The limit is 500 euros. Ask finance."
    )
    quote = choose_quote(body, claim="the limit is 500 euros")
    assert quote.text == "The limit is 500 euros."


def test_the_source_travels_with_the_quote():
    body = passage("The limit is 500 euros.")
    assert choose_quote(body, claim="limit 500").source == "handbook"


def test_nothing_is_quoted_when_the_passage_does_not_say_it():
    body = passage("Expenses are reviewed monthly.")
    assert choose_quote(body, claim="the limit is 500 euros") is None


def test_the_best_matching_sentence_wins_over_a_weaker_one():
    body = passage("The limit applies. The limit is 500 euros for travel.")
    quote = choose_quote(body, claim="limit 500 euros travel")
    assert quote.text == "The limit is 500 euros for travel."


def test_a_neighbouring_sentence_is_added_when_the_quote_cannot_stand_alone():
    body = passage("Travel has its own rules. It is capped at 500 euros.")
    quote = choose_quote(body, claim="travel capped at 500 euros")
    assert quote.text == "Travel has its own rules. It is capped at 500 euros."


def test_a_quote_that_stands_alone_is_left_alone():
    body = passage("Travel has its own rules. The travel cap is 500 euros.")
    quote = choose_quote(body, claim="travel cap 500 euros")
    assert quote.text == "The travel cap is 500 euros."


def test_a_long_sentence_is_shortened_around_what_matters():
    long = (
        "Under the revised policy agreed last spring by the finance committee "
        "after a lengthy consultation, the travel limit is 500 euros per trip "
        "unless a director has approved something larger in advance."
    )
    quote = choose_quote(passage(long), claim="travel limit 500 euros", max_words=12)
    assert len(quote.text.split()) <= 12


def test_a_shortened_quote_says_it_was_shortened():
    long = " ".join(["word"] * 40 + ["the", "limit", "is", "500"] + ["word"] * 40)
    quote = choose_quote(passage(long), claim="the limit is 500", max_words=12)
    assert quote.shortened is True


def test_a_whole_sentence_is_not_marked_as_shortened():
    body = passage("The limit is 500 euros.")
    assert choose_quote(body, claim="limit 500 euros").shortened is False


def test_a_shortened_quote_keeps_the_words_that_matter():
    long = " ".join(["word"] * 40 + ["the", "limit", "is", "500"] + ["word"] * 40)
    quote = choose_quote(passage(long), claim="the limit is 500", max_words=12)
    assert "500" in quote.text


def test_where_in_the_source_the_quote_came_from_is_reported():
    body = passage("Expenses are reviewed monthly. The limit is 500 euros.")
    quote = choose_quote(body, claim="the limit is 500 euros")
    assert quote.offset == body.text.index("The limit")


def test_an_empty_claim_is_refused():
    with pytest.raises(ValueError):
        choose_quote(passage("anything"), claim="   ")


def test_an_empty_passage_is_refused():
    with pytest.raises(ValueError):
        Passage(source="handbook", text="  ")


def test_a_quote_cannot_be_asked_to_be_shorter_than_nothing():
    with pytest.raises(ValueError):
        choose_quote(passage("The limit is 500."), claim="limit", max_words=0)
