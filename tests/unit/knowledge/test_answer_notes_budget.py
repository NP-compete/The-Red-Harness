"""A note another middleware left is not overwritten."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)


def stamped(already: dict | None) -> dict:
    messages = [
        HumanMessage(content="what are the approval rules"),
        ToolMessage(content="Approvals go to the line manager.", tool_call_id="1"),
    ]
    reply = AIMessage(content="Approvals go to the line manager.")
    if already is not None:
        reply.additional_kwargs["answer_notes"] = already

    response = build_answer_notes_middleware().wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    return response.result[0].additional_kwargs.get("answer_notes", {})


def test_a_budget_note_already_there_survives():
    already = {"budget": {"withheld": ["grep"], "scope": "block", "limit": 3}}
    assert stamped(already)["budget"]["withheld"] == ["grep"]


def test_the_scope_survives_with_it():
    already = {"budget": {"withheld": ["grep"], "scope": "conversation", "limit": 5}}
    assert stamped(already)["budget"]["scope"] == "conversation"


def test_what_this_middleware_measures_is_still_written():
    already = {"budget": {"withheld": ["grep"], "scope": "block", "limit": 3}}
    assert "figures" in stamped(already)


def test_an_answer_with_no_budget_note_gains_none():
    assert "budget" not in stamped(None)
