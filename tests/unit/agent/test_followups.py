"""Offering next questions that this agent could actually answer."""

from __future__ import annotations

import pytest

from agent.src.agent.followups import Candidate, Context, choose_followups


def candidate(text: str, needs: tuple[str, ...] = (), **kwargs) -> Candidate:
    defaults = {"about": "expenses"}
    defaults.update(kwargs)
    return Candidate(text=text, needs=needs, **defaults)


def context(**kwargs) -> Context:
    defaults = {
        "available_tools": ("search", "chart"),
        "topics_covered": ("expenses",),
        "already_asked": (),
        "answer_was_complete": True,
        "limit": 3,
    }
    defaults.update(kwargs)
    return Context(**defaults)


CANDIDATES = [
    candidate("Show the trend over the year", needs=("chart",)),
    candidate("Who approves these?", needs=()),
    candidate("Export this to a spreadsheet", needs=("export",)),
]


def test_a_followup_this_agent_can_do_is_offered():
    chosen = choose_followups(CANDIDATES, context=context())
    assert "Show the trend over the year" in [item.text for item in chosen.offered]


def test_a_followup_needing_a_missing_tool_is_not_offered():
    chosen = choose_followups(CANDIDATES, context=context())
    assert "Export this to a spreadsheet" not in [item.text for item in chosen.offered]


def test_a_followup_needing_nothing_is_always_possible():
    chosen = choose_followups(CANDIDATES, context=context(available_tools=()))
    assert [item.text for item in chosen.offered] == ["Who approves these?"]


def test_something_already_asked_is_not_offered_again():
    asked = context(already_asked=("Who approves these?",))
    chosen = choose_followups(CANDIDATES, context=asked)
    assert "Who approves these?" not in [item.text for item in chosen.offered]


def test_no_more_than_the_limit_are_offered():
    many = [candidate(f"Question {n}") for n in range(10)]
    assert len(choose_followups(many, context=context(limit=3)).offered) == 3


def test_nothing_is_offered_when_the_answer_was_incomplete():
    chosen = choose_followups(CANDIDATES, context=context(answer_was_complete=False))
    assert chosen.offered == ()


def test_an_incomplete_answer_says_why_nothing_is_offered():
    chosen = choose_followups(CANDIDATES, context=context(answer_was_complete=False))
    assert "unanswered" in chosen.reason


def test_a_followup_about_an_uncovered_topic_is_not_offered():
    stray = [candidate("What about payroll?", about="payroll")]
    assert choose_followups(stray, context=context()).offered == ()


def test_why_each_followup_was_offered_is_recorded():
    chosen = choose_followups(CANDIDATES, context=context())
    assert chosen.offered[0].because == "expenses"


def test_what_was_set_aside_is_counted():
    chosen = choose_followups(CANDIDATES, context=context())
    assert chosen.set_aside == 1


def test_duplicate_suggestions_are_offered_once():
    repeated = [candidate("Who approves these?"), candidate("Who approves these?")]
    assert len(choose_followups(repeated, context=context()).offered) == 1


def test_the_order_given_is_kept():
    chosen = choose_followups(CANDIDATES, context=context())
    assert [item.text for item in chosen.offered] == [
        "Show the trend over the year",
        "Who approves these?",
    ]


def test_having_nothing_to_offer_is_not_an_error():
    assert choose_followups([], context=context()).offered == ()


def test_a_followup_with_no_text_is_refused():
    with pytest.raises(ValueError):
        candidate("   ")


def test_a_limit_of_nothing_is_refused():
    with pytest.raises(ValueError):
        context(limit=0)
