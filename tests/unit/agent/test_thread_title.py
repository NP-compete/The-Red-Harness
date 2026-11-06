"""Giving a conversation a name people can scan a list by."""

from __future__ import annotations

import pytest

from agent.src.agent.thread_title import Source, suggest_title


def test_a_short_first_message_becomes_the_title():
    assert suggest_title("Summarise the Q3 numbers").text == "Summarise the Q3 numbers"


def test_a_long_first_message_is_shortened():
    long = "Please summarise the quarterly numbers for the finance team before Friday"
    assert len(suggest_title(long).text) <= 48


def test_a_shortened_title_does_not_cut_a_word_in_half():
    long = "Please summarise the quarterly numbers for the finance team before Friday"
    assert not suggest_title(long).text.rstrip("…").endswith(" ")
    assert " " not in suggest_title(long).text[-2:]


def test_a_shortened_title_shows_that_it_was_shortened():
    long = "Please summarise the quarterly numbers for the finance team before Friday"
    assert suggest_title(long).text.endswith("…")


def test_politeness_is_dropped_from_the_front():
    assert (
        suggest_title("please can you summarise the numbers").text
        == "Summarise the numbers"
    )


def test_the_title_starts_with_a_capital():
    assert suggest_title("summarise the numbers").text[0] == "S"


def test_a_question_keeps_its_question_mark():
    assert (
        suggest_title("what is the expense limit?").text == "What is the expense limit?"
    )


def test_a_title_is_a_single_line():
    assert "\n" not in suggest_title("first line\nsecond line").text


def test_a_message_that_is_only_an_attachment_is_named_for_it():
    assert suggest_title("", attachment="report.pdf").text == "About report.pdf"


def test_an_empty_conversation_gets_a_plain_name():
    assert suggest_title("").text == "New conversation"


def test_an_empty_conversation_is_marked_as_a_placeholder():
    assert suggest_title("").source is Source.PLACEHOLDER


def test_a_title_from_the_message_says_where_it_came_from():
    assert suggest_title("Summarise the numbers").source is Source.FIRST_MESSAGE


def test_a_message_holding_a_secret_is_not_used_as_a_title():
    secret = "my api key is 9f2b7c1e4a6d8035bb17c9e2f4a6d803, please check it"
    assert suggest_title(secret).source is Source.PLACEHOLDER


def test_a_message_holding_an_email_address_is_not_used_as_a_title():
    assert (
        suggest_title("email ana@example.com about the report").source
        is Source.PLACEHOLDER
    )


def test_a_sensitive_message_still_gets_a_usable_name():
    assert (
        suggest_title("my api key is 9f2b7c1e4a6d8035bb17c9e2f4a6d803").text
        == "New conversation"
    )


def test_a_person_set_title_is_never_replaced():
    assert (
        suggest_title(
            "Summarise the numbers", existing="Quarterly review", pinned=True
        ).text
        == "Quarterly review"
    )


def test_an_automatic_title_may_be_replaced():
    assert (
        suggest_title("Summarise the numbers", existing="New conversation").text
        == "Summarise the numbers"
    )


def test_whitespace_only_input_is_a_placeholder():
    assert suggest_title("   ").source is Source.PLACEHOLDER


def test_a_title_is_never_empty():
    assert suggest_title("...").text != ""


def test_a_negative_length_limit_is_refused():
    with pytest.raises(ValueError):
        suggest_title("anything", max_length=0)
