"""Turning a typed command into the request it stands for."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from agent.src.agent.command_middleware import build_command_middleware


def run(*contents: str):
    messages = [
        HumanMessage(content=c) if i % 2 == 0 else AIMessage(content=c)
        for i, c in enumerate(contents)
    ]
    seen: dict = {}
    middleware = build_command_middleware()

    def handler(request):
        seen["messages"] = request.messages
        return SimpleNamespace(result=[AIMessage(content="ok")])

    middleware.wrap_model_call(SimpleNamespace(messages=messages), handler)
    return seen["messages"]


def test_an_ordinary_question_reaches_the_model_unchanged():
    sent = run("what is the travel limit?")
    assert sent[-1].content == "what is the travel limit?"


def test_a_command_is_expanded_before_the_model_sees_it():
    sent = run("/summarise")
    assert sent[-1].content.startswith("Summarise the conversation so far")


def test_the_argument_travels_with_it():
    sent = run("/summarise the third quarter")
    assert "the third quarter" in sent[-1].content


def test_an_unknown_command_is_left_as_typed():
    sent = run("/nonsense please")
    assert sent[-1].content == "/nonsense please"


def test_only_the_newest_message_is_rewritten():
    sent = run("/summarise", "an earlier answer", "what is the travel limit?")
    assert sent[0].content == "/summarise"


def test_an_earlier_answer_is_left_alone():
    sent = run("/summarise", "an earlier answer", "what is the travel limit?")
    assert sent[1].content == "an earlier answer"


def test_a_turn_with_no_messages_is_survived():
    assert run() == []


def test_the_rewritten_message_is_still_from_the_person():
    sent = run("/summarise")
    assert sent[-1].type == "human"
