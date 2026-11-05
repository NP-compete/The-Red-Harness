"""Noticing a turn that is going round in circles."""

from __future__ import annotations

import json
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)


def call(tool: str, args: dict, result: str = "ok") -> list:
    """One round trip: the model asking for a tool, and what came back."""
    asked = AIMessage(
        content="",
        tool_calls=[{"name": tool, "args": args, "id": f"{tool}-{json.dumps(args)}"}],
    )
    came_back = ToolMessage(content=result, tool_call_id=f"{tool}-{json.dumps(args)}")
    return [asked, came_back]


def run(history: list) -> dict:
    messages: list = [HumanMessage(content="find the approval rules"), *history]
    reply = AIMessage(content="Here is what I found.")
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[reply]),
    )
    return response.result[0].additional_kwargs.get("answer_notes", {})


def test_a_turn_that_made_progress_says_nothing_about_looping():
    history = [*call("search", {"q": "limit"}), *call("fetch", {"id": "1"})]
    assert "loop" not in run(history)


def test_the_same_call_three_times_is_called_out():
    history = [c for _ in range(3) for c in call("search", {"q": "limit"})]
    assert run(history)["loop"]["pattern"] == "repeating"


def test_the_repeated_tool_is_named():
    history = [c for _ in range(3) for c in call("search", {"q": "limit"})]
    assert run(history)["loop"]["repeated"] == "search"


def test_how_many_times_it_repeated_is_recorded():
    history = [c for _ in range(3) for c in call("search", {"q": "limit"})]
    assert run(history)["loop"]["times"] == 3


def test_the_same_call_with_different_arguments_is_progress():
    history = [
        *call("search", {"q": "a"}),
        *call("search", {"q": "b"}),
        *call("search", {"q": "c"}),
    ]
    assert "loop" not in run(history)


def test_going_back_and_forth_is_called_out():
    history = [
        c
        for _ in range(3)
        for c in [*call("search", {"q": "a"}), *call("fetch", {"id": "1"})]
    ]
    assert run(history)["loop"]["pattern"] == "alternating"


def test_the_same_failure_over_and_over_is_called_out():
    history = [
        c
        for i in range(4)
        for c in call("search", {"q": str(i)}, result="connection refused")
    ]
    assert run(history)["loop"]["pattern"] == "same-failure"


def test_a_turn_with_no_tool_calls_says_nothing_about_looping():
    assert "loop" not in run([])
