"""The closest thing that was read to a sentence nothing backs up."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)

READ = "The travel limit is 500 euros per trip for every employee."


def run(answer: str, read: list[str] | None = None) -> dict:
    messages: list = [HumanMessage(content="what is the travel limit?")]
    for i, text in enumerate([READ] if read is None else read):
        messages.append(ToolMessage(content=text, tool_call_id=f"t{i}"))

    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[AIMessage(content=answer)]),
    )
    return response.result[0].additional_kwargs.get("answer_notes", {})


def test_a_flagged_sentence_carries_the_nearest_thing_read():
    """Paraphrase and invention both flag; only one has a near match."""
    notes = run("Each employee may spend up to 500 euros on any single trip.")
    nearest = notes["claims"][0]["nearest"]
    assert "500 euros per trip" in nearest["text"]


def test_the_nearest_match_says_where_it_came_from():
    notes = run("Each employee may spend up to 500 euros on any single trip.")
    assert notes["claims"][0]["nearest"]["source"]


def test_a_sentence_with_nothing_like_it_carries_no_match():
    notes = run("Reimbursement needs a director signature.")
    assert notes["claims"][0].get("nearest") is None


def test_the_closest_source_is_the_one_quoted():
    notes = run(
        "Each employee may spend up to 500 euros on any single trip.",
        read=["Parking is free at every office.", READ],
    )
    assert "500 euros" in notes["claims"][0]["nearest"]["text"]


def test_a_supported_sentence_is_not_reported_at_all():
    notes = run(READ)
    assert notes["claims"] == []


def test_a_long_match_is_marked_as_shortened():
    long_read = " ".join(["The travel limit is 500 euros per trip"] + ["and"] * 80)
    notes = run("Each employee may spend 500 euros on a trip.", read=[long_read])
    assert notes["claims"][0]["nearest"]["shortened"] is True
