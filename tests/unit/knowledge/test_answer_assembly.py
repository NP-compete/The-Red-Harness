"""Laying out an answer part by part, with its sources attached."""

from __future__ import annotations

import pytest

from agent.src.knowledge.answer_assembly import Answered, assemble

ANSWERS = (
    Answered(
        question="what is the expense limit",
        text="The limit is 500.",
        sources=("handbook",),
    ),
    Answered(
        question="who approves it", text="A manager.", sources=("policy", "handbook")
    ),
)


def test_each_part_becomes_a_section():
    result = assemble(ANSWERS, asked=("what is the expense limit", "who approves it"))
    assert [section.question for section in result.sections] == [
        "what is the expense limit",
        "who approves it",
    ]


def test_the_sections_follow_the_order_asked():
    reversed_answers = (ANSWERS[1], ANSWERS[0])
    result = assemble(
        reversed_answers, asked=("what is the expense limit", "who approves it")
    )
    assert result.sections[0].question == "what is the expense limit"


def test_each_section_carries_its_own_sources():
    result = assemble(ANSWERS, asked=("what is the expense limit", "who approves it"))
    assert result.sections[1].sources == ("handbook", "policy")


def test_a_part_with_no_answer_becomes_a_gap():
    result = assemble(
        ANSWERS[:1], asked=("what is the expense limit", "who approves it")
    )
    assert result.sections[1].answered is False


def test_a_gap_says_plainly_that_nothing_was_found():
    result = assemble(
        ANSWERS[:1], asked=("what is the expense limit", "who approves it")
    )
    assert result.sections[1].text == "No answer was found for this."


def test_a_gap_carries_no_sources():
    result = assemble(
        ANSWERS[:1], asked=("what is the expense limit", "who approves it")
    )
    assert result.sections[1].sources == ()


def test_an_answer_with_no_sources_is_marked_unsourced():
    unsourced = (Answered(question="a", text="something", sources=()),)
    assert assemble(unsourced, asked=("a",)).sections[0].unsourced is True


def test_a_sourced_answer_is_not_marked_unsourced():
    result = assemble(ANSWERS, asked=("what is the expense limit", "who approves it"))
    assert result.sections[0].unsourced is False


def test_every_source_used_is_collected_once():
    result = assemble(ANSWERS, asked=("what is the expense limit", "who approves it"))
    assert result.all_sources == ("handbook", "policy")


def test_whether_the_answer_is_complete_is_reported():
    result = assemble(ANSWERS, asked=("what is the expense limit", "who approves it"))
    assert result.complete is True


def test_a_missing_part_makes_the_answer_incomplete():
    result = assemble(
        ANSWERS[:1], asked=("what is the expense limit", "who approves it")
    )
    assert result.complete is False


def test_an_answer_to_something_that_was_not_asked_is_refused():
    stray = (Answered(question="unasked", text="x", sources=()),)
    with pytest.raises(ValueError):
        assemble(stray, asked=("what is the expense limit",))


def test_two_answers_to_the_same_part_are_refused():
    twice = (
        Answered(question="a", text="one", sources=()),
        Answered(question="a", text="two", sources=()),
    )
    with pytest.raises(ValueError):
        assemble(twice, asked=("a",))


def test_asking_nothing_is_refused():
    with pytest.raises(ValueError):
        assemble(ANSWERS, asked=())


def test_an_answer_with_no_text_is_refused():
    with pytest.raises(ValueError):
        Answered(question="a", text="   ", sources=())


def test_a_single_part_answer_needs_no_headings():
    result = assemble(ANSWERS[:1], asked=("what is the expense limit",))
    assert result.use_headings is False


def test_a_multi_part_answer_uses_headings():
    result = assemble(ANSWERS, asked=("what is the expense limit", "who approves it"))
    assert result.use_headings is True
