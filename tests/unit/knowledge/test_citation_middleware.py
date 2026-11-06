"""Putting the citations on the answer."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from agent.src.knowledge.citation_middleware import stamp_citations

LEAVE = {
    "id": "corpus:leave.md",
    "title": "leave",
    "text": "Staff accrue 25 days of annual leave per year.",
    "scope": "agent",
}
EXPENSES = {
    "id": "corpus:expenses.md",
    "title": "expenses",
    "text": "Claims over 750 require a receipt and manager approval.",
    "scope": "agent",
}


def _tool_message(documents: list[dict]) -> Any:
    return SimpleNamespace(type="tool", name="search_documents", artifact=documents)


def _answer(text: str) -> Any:
    return SimpleNamespace(content=text, additional_kwargs={})


def _notes(message: Any) -> dict:
    return message.additional_kwargs.get("answer_notes") or {}


class TestWhenSomethingWasRetrieved:
    def test_a_borrowed_document_is_cited(self):
        answer = _answer("Staff accrue 25 days of annual leave per year.")
        stamp_citations(answer, [_tool_message([LEAVE])])
        assert _notes(answer)["citations"][0]["document_id"] == "corpus:leave.md"

    def test_one_that_was_only_retrieved_is_not(self):
        answer = _answer("Staff accrue 25 days of annual leave per year.")
        stamp_citations(answer, [_tool_message([LEAVE, EXPENSES])])
        assert len(_notes(answer)["citations"]) == 1

    def test_an_answer_from_memory_cites_nothing(self):
        answer = _answer("I am not sure about that.")
        stamp_citations(answer, [_tool_message([LEAVE])])
        assert "citations" not in _notes(answer)

    def test_nothing_is_written_when_there_is_nothing_to_say(self):
        answer = _answer("I am not sure about that.")
        stamp_citations(answer, [_tool_message([LEAVE])])
        assert _notes(answer) == {}


class TestWhenNothingWasRetrieved:
    def test_a_turn_with_no_lookup_is_left_alone(self):
        answer = _answer("Staff accrue 25 days of annual leave per year.")
        stamp_citations(answer, [])
        assert _notes(answer) == {}

    def test_a_lookup_that_found_nothing_leaves_it_alone(self):
        answer = _answer("Staff accrue 25 days.")
        stamp_citations(answer, [_tool_message([])])
        assert _notes(answer) == {}

    def test_another_tool_entirely_is_ignored(self):
        other = SimpleNamespace(type="tool", name="execute_sql", artifact=[LEAVE])
        answer = _answer("Staff accrue 25 days of annual leave per year.")
        stamp_citations(answer, [other])
        assert _notes(answer) == {}


class TestSeveralLookupsInOneTurn:
    def test_documents_from_all_of_them_are_considered(self):
        answer = _answer(
            "Staff accrue 25 days of annual leave per year. "
            "Claims over 750 require a receipt and manager approval."
        )
        stamp_citations(answer, [_tool_message([LEAVE]), _tool_message([EXPENSES])])
        assert len(_notes(answer)["citations"]) == 2

    def test_the_same_document_twice_is_cited_once(self):
        answer = _answer("Staff accrue 25 days of annual leave per year.")
        stamp_citations(answer, [_tool_message([LEAVE]), _tool_message([LEAVE])])
        assert len(_notes(answer)["citations"]) == 1


class TestItDoesNotTrampleTheOtherNotes:
    def test_an_existing_note_survives(self):
        answer = _answer("Staff accrue 25 days of annual leave per year.")
        answer.additional_kwargs["answer_notes"] = {"budget": {"spent": True}}
        stamp_citations(answer, [_tool_message([LEAVE])])
        assert _notes(answer)["budget"] == {"spent": True}

    def test_and_the_citations_are_added_beside_it(self):
        answer = _answer("Staff accrue 25 days of annual leave per year.")
        answer.additional_kwargs["answer_notes"] = {"budget": {"spent": True}}
        stamp_citations(answer, [_tool_message([LEAVE])])
        assert "citations" in _notes(answer)


class TestItNeverCostsTheTurn:
    def test_an_unreadable_artifact_is_survived(self):
        broken = SimpleNamespace(
            type="tool", name="search_documents", artifact="nonsense"
        )
        answer = _answer("Staff accrue 25 days.")
        stamp_citations(answer, [broken])
        assert _notes(answer) == {}

    def test_a_message_with_no_place_to_write_is_survived(self):
        answer = SimpleNamespace(content="Staff accrue 25 days.")
        stamp_citations(answer, [_tool_message([LEAVE])])


class TestTheGraphUsesIt:
    def test_the_middleware_is_built_somewhere(self):
        import inspect

        from agent.src.knowledge import citation_middleware

        assert "AgentMiddleware" in inspect.getsource(citation_middleware)

    def test_it_is_only_added_when_the_library_is_on(self):
        from agent.src.knowledge.citation_middleware import (
            build_citation_middleware,
        )
        from agent.src.knowledge.config import Knowledge

        assert build_citation_middleware(config=Knowledge()) is None

    def test_the_graph_adds_it(self):
        import inspect

        from agent.aegra import graph

        assert "build_citation_middleware" in inspect.getsource(graph)
