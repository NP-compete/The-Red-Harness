"""Where one sentence of an answer ends and the next begins."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.src.knowledge.answer_notes_middleware import (
    build_answer_notes_middleware,
)

READ = "Nothing here resembles the answer at all."


def claims(answer: str) -> list[str]:
    messages: list = [
        HumanMessage(content="what did you do?"),
        ToolMessage(content=READ, tool_call_id="t0"),
    ]
    middleware = build_answer_notes_middleware()
    response = middleware.wrap_model_call(
        SimpleNamespace(messages=messages),
        lambda _request: SimpleNamespace(result=[AIMessage(content=answer)]),
    )
    notes = response.result[0].additional_kwargs.get("answer_notes", {})
    return [claim["text"] for claim in notes.get("claims", [])]


def test_two_plain_sentences_are_two_claims():
    assert claims("The fee is 500 pounds. The limit is lower.") == [
        "The fee is 500 pounds.",
        "The limit is lower.",
    ]


def test_a_file_name_does_not_end_a_sentence():
    assert claims("Checking the folder for rates.md now.") == [
        "Checking the folder for rates.md now."
    ]


def test_a_decimal_does_not_end_a_sentence():
    assert claims("The rate is 3.5 percent this year.") == [
        "The rate is 3.5 percent this year."
    ]


def test_a_path_does_not_end_a_sentence():
    assert claims("Looking in /srv/data/v1.2/reports for it.") == [
        "Looking in /srv/data/v1.2/reports for it."
    ]


def test_a_question_and_an_exclamation_each_end_one():
    assert claims("Is that right? It is! Good.") == [
        "Is that right?",
        "It is!",
        "Good.",
    ]


def test_a_trailing_fragment_is_kept():
    assert claims("The fee is 500 pounds. Still checking") == [
        "The fee is 500 pounds.",
        "Still checking",
    ]


def test_a_wordless_fragment_is_not_a_claim_of_its_own():
    """Trailing punctuation stays with the sentence it followed."""
    found = claims("The fee is 500 pounds. ...")
    assert len(found) == 1
    assert found[0].startswith("The fee is 500 pounds.")
