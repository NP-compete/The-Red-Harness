"""Stamping an answer with what its figures rest on."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)


def run(answer: str, read: list[str]) -> dict:
    messages = [HumanMessage(content="what is the limit?")]
    for i, text in enumerate(read):
        messages.append(ToolMessage(content=text, tool_call_id=f"t{i}"))

    reply = AIMessage(content=answer)
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    message = response.result[0]
    return message.additional_kwargs.get("answer_notes", {})


def test_an_answer_whose_figures_appear_in_what_was_read_is_not_flagged():
    notes = run("The limit is 500 euros.", ["The travel limit is 500 euros."])
    assert notes["figures"]["unsupported"] == []


def test_a_figure_that_appears_nowhere_is_flagged():
    notes = run("The limit is 750 euros.", ["The travel limit is 500 euros."])
    assert notes["figures"]["unsupported"] == ["750"]


def test_how_many_figures_were_checked_is_recorded():
    notes = run("Between 500 and 900.", ["The travel limit is 500 euros."])
    assert notes["figures"]["checked"] == 2


def test_every_tool_result_in_the_turn_counts_as_read():
    notes = run("The limit is 900.", ["nothing here", "it is 900"])
    assert notes["figures"]["unsupported"] == []


def test_an_answer_with_no_figures_has_nothing_to_check():
    notes = run("The limit is generous.", ["The travel limit is 500 euros."])
    assert notes["figures"] == {"checked": 0, "unsupported": []}


def test_an_answer_with_nothing_read_is_not_stamped():
    assert run("The limit is 500 euros.", []) == {}


def test_the_answer_itself_is_left_alone():
    messages = [
        HumanMessage(content="q"),
        ToolMessage(content="500", tool_call_id="t0"),
    ]
    reply = AIMessage(content="The limit is 750.")
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    assert response.result[0].content == "The limit is 750."


def test_a_turn_that_produced_no_message_is_survived():
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=[]),
        lambda _request: SimpleNamespace(result=[]),
    )
    assert response.result == []


def test_a_broken_message_does_not_break_the_turn():
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=[HumanMessage(content="q")]),
        lambda _request: SimpleNamespace(result=[object()]),
    )
    assert response is not None
