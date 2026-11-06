"""Which sentences of an answer appear in what the turn read."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)

READ = ["The travel limit is 500 euros per trip for every employee."]


def run(answer: str, read: list[str] | None = None) -> dict:
    messages: list = [HumanMessage(content="what is the travel limit?")]
    for i, text in enumerate(READ if read is None else read):
        messages.append(ToolMessage(content=text, tool_call_id=f"t{i}"))

    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[AIMessage(content=answer)]),
    )
    return response.result[0].additional_kwargs.get("answer_notes", {})


def test_a_sentence_taken_from_what_was_read_is_not_flagged():
    notes = run("The travel limit is 500 euros per trip for every employee.")
    assert notes["claims"] == []


def test_a_sentence_appearing_nowhere_is_flagged():
    notes = run(
        "Reimbursement needs a director signature within thirty days of travel."
    )
    assert notes["claims"] == [
        {
            "text": "Reimbursement needs a director signature within thirty days of travel.",
            "supported": False,
            "contradicted": False,
            "nearest": None,
        }
    ]


def test_only_the_unsupported_sentence_is_flagged():
    notes = run(
        "The travel limit is 500 euros per trip for every employee. "
        "Reimbursement needs a director signature within thirty days of travel."
    )
    assert [claim["text"] for claim in notes["claims"]] == [
        "Reimbursement needs a director signature within thirty days of travel."
    ]


def test_a_sentence_that_changes_a_figure_is_flagged():
    notes = run("The travel limit is 750 euros per trip for every employee.")
    assert notes["claims"][0]["supported"] is False


def test_an_answer_with_nothing_read_flags_nothing():
    assert run("The travel limit is 500 euros.", []) == {}
