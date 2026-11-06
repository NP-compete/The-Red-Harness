"""Whether the answer went near every part of what was asked."""

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


def run(asked: str, answer: str, read: list[str] | None = None) -> dict:
    messages: list = [HumanMessage(content=asked)]
    for i, text in enumerate(READ if read is None else read):
        messages.append(ToolMessage(content=text, tool_call_id=f"t{i}"))

    reply = AIMessage(content=answer)
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    return response.result[0].additional_kwargs.get("answer_notes", {})


def test_an_answer_covering_the_whole_question_is_not_hedged_for_coverage():
    notes = run(
        "What is the travel limit?",
        "The travel limit is 500 euros per trip for every employee.",
    )
    assert not any("part of what was asked" in c for c in notes["concerns"])


def test_an_answer_ignoring_half_a_compound_question_is_hedged():
    notes = run(
        "What is the travel limit? Also when must receipts be filed?",
        "The travel limit is 500 euros per trip for every employee.",
    )
    assert any("part of what was asked" in c for c in notes["concerns"])


def test_a_half_answered_question_is_not_stated_plainly():
    notes = run(
        "What is the travel limit? Also when must receipts be filed?",
        "The travel limit is 500 euros per trip for every employee.",
    )
    assert notes["stance"] == "hedged"


def test_an_answer_covering_both_parts_is_stated_plainly():
    notes = run(
        "What is the travel limit? Also when must receipts be filed?",
        "The travel limit is 500 euros per trip, and receipts must be filed "
        "within thirty days of the trip.",
    )
    assert notes["stance"] == "plain"


def test_a_question_that_cannot_be_split_raises_no_coverage_concern():
    notes = run("?", "The travel limit is 500 euros per trip for every employee.")
    assert not any("part of what was asked" in c for c in notes["concerns"])


def test_a_turn_with_no_question_raises_no_coverage_concern():
    reply = AIMessage(
        content="The travel limit is 500 euros per trip for every employee."
    )
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=[ToolMessage(content=READ[0], tool_call_id="t0")]),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    notes = response.result[0].additional_kwargs.get("answer_notes", {})
    assert not any("part of what was asked" in c for c in notes["concerns"])


def test_the_most_recent_question_is_the_one_measured():
    messages: list = [
        HumanMessage(
            content="What is the travel limit? Also when must receipts be filed?"
        ),
        AIMessage(content="an earlier answer"),
        HumanMessage(content="What is the travel limit?"),
        ToolMessage(content=READ[0], tool_call_id="t0"),
    ]
    reply = AIMessage(
        content="The travel limit is 500 euros per trip for every employee."
    )
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    notes = response.result[0].additional_kwargs["answer_notes"]
    assert not any("part of what was asked" in c for c in notes["concerns"])
