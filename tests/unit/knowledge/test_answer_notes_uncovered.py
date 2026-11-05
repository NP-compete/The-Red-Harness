"""Naming the parts of a question the answer never reached."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)

READ = [
    "The travel limit is 500 euros per trip for every employee.",
    "Receipts for travel must be filed within thirty days of the trip.",
]

BOTH = "What is the travel limit? Also when must receipts be filed?"


def run(asked: str, answer: str) -> dict:
    messages: list = [HumanMessage(content=asked)]
    for i, text in enumerate(READ):
        messages.append(ToolMessage(content=text, tool_call_id=f"t{i}"))

    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[AIMessage(content=answer)]),
    )
    return response.result[0].additional_kwargs.get("answer_notes", {})


def test_an_answer_covering_everything_names_nothing_as_missing():
    notes = run(
        BOTH,
        "The travel limit is 500 euros per trip and receipts must be filed "
        "within thirty days of the trip.",
    )
    assert "coverage" not in notes


def test_a_half_answered_question_names_the_half_that_was_missed():
    notes = run(BOTH, "The travel limit is 500 euros per trip for every employee.")
    assert notes["coverage"]["uncovered"] == ["Also when must receipts be filed"]


def test_how_much_of_the_question_was_answered_is_recorded():
    notes = run(BOTH, "The travel limit is 500 euros per trip for every employee.")
    assert notes["coverage"]["share"] == 0.5


def test_how_many_parts_were_asked_is_recorded():
    notes = run(BOTH, "The travel limit is 500 euros per trip for every employee.")
    assert notes["coverage"]["part_count"] == 2


def test_a_single_part_question_left_unanswered_is_named():
    notes = run(
        "When must receipts be filed?",
        "I could not find anything about that in the handbook.",
    )
    assert notes["coverage"]["uncovered"] == ["When must receipts be filed"]


def test_a_question_that_cannot_be_split_reports_no_coverage():
    assert "coverage" not in run("?", "The travel limit is 500 euros per trip.")
