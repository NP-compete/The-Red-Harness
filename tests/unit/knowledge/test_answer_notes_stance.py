"""How firmly an answer is stated, worked out from the turn that produced it."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)


def run(answer: str, read: list[str]) -> dict:
    messages: list = [HumanMessage(content="what is the limit?")]
    for i, text in enumerate(read):
        messages.append(ToolMessage(content=text, tool_call_id=f"t{i}"))

    reply = AIMessage(content=answer)
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    return response.result[0].additional_kwargs.get("answer_notes", {})


GROUNDED = [
    "The travel limit is 500 euros per trip for every employee.",
    "The travel limit of 500 euros per trip applies to every employee.",
]


def test_an_answer_resting_on_several_agreeing_sources_is_stated_plainly():
    notes = run("The travel limit is 500 euros per trip for every employee.", GROUNDED)
    assert notes["stance"] == "plain"


def test_an_answer_resting_on_one_source_is_hedged():
    notes = run(
        "The travel limit is 500 euros per trip for every employee.", GROUNDED[:1]
    )
    assert notes["stance"] == "hedged"


def test_a_hedged_answer_says_what_is_shaky():
    notes = run(
        "The travel limit is 500 euros per trip for every employee.", GROUNDED[:1]
    )
    assert "single source" in notes["hedge"]


def test_an_answer_whose_claims_are_not_in_what_was_read_is_declined():
    notes = run(
        "Reimbursement requires a director signature within thirty days of travel.",
        GROUNDED,
    )
    assert notes["stance"] == "decline"


def test_a_plainly_stated_answer_carries_no_concerns():
    notes = run("The travel limit is 500 euros per trip for every employee.", GROUNDED)
    assert notes["concerns"] == []


def test_the_stance_is_left_off_when_nothing_was_read():
    assert run("The travel limit is 500 euros.", []) == {}


def test_an_answer_with_no_figures_still_carries_a_stance():
    notes = run("The travel limit applies to every employee per trip.", GROUNDED)
    assert "stance" in notes


def test_the_figures_check_still_travels_alongside_the_stance():
    notes = run("The travel limit is 750 euros per trip for every employee.", GROUNDED)
    assert notes["figures"]["unsupported"] == ["750"]
