"""Naming the documents an answer actually came from."""

from __future__ import annotations

from agent.src.knowledge.citing import cite
from agent.src.knowledge.retrieval import Found
from agent.src.knowledge.scopes import Scope
from agent.src.knowledge.store import Document

LEAVE = Document(
    id="corpus:hr/leave.md",
    title="leave",
    text="Staff accrue 25 days of annual leave per year.",
    scope=Scope.AGENT,
)
EXPENSES = Document(
    id="corpus:expenses.md",
    title="expenses",
    text="Claims over 750 require a receipt and manager approval.",
    scope=Scope.AGENT,
)


def _found(*documents) -> Found:
    return Found(documents=list(documents), scope=Scope.AGENT, searched=(Scope.AGENT,))


class TestWhatIsCited:
    def test_the_document_an_answer_borrowed_from(self):
        answer = "Staff accrue 25 days of annual leave per year."
        found = cite(answer=answer, found=_found(LEAVE))
        assert [c.document_id for c in found] == ["corpus:hr/leave.md"]

    def test_not_one_that_was_merely_retrieved(self):
        answer = "Staff accrue 25 days of annual leave per year."
        found = cite(answer=answer, found=_found(LEAVE, EXPENSES))
        assert [c.document_id for c in found] == ["corpus:hr/leave.md"]

    def test_several_when_several_were_used(self):
        answer = (
            "Staff accrue 25 days of annual leave per year. "
            "Claims over 750 require a receipt and manager approval."
        )
        found = cite(answer=answer, found=_found(LEAVE, EXPENSES))
        assert len(found) == 2

    def test_an_answer_from_nothing_cites_nothing(self):
        found = cite(answer="I am not sure about that.", found=_found(LEAVE))
        assert found == []

    def test_a_retrieval_that_found_nothing_cites_nothing(self):
        found = cite(answer="Staff accrue 25 days.", found=Found())
        assert found == []

    def test_an_empty_answer_cites_nothing(self):
        assert cite(answer="", found=_found(LEAVE)) == []


class TestWhatACitationCarries:
    @staticmethod
    def _one():
        answer = "Staff accrue 25 days of annual leave per year."
        return cite(answer=answer, found=_found(LEAVE))[0]

    def test_the_document_it_points_at(self):
        assert self._one().document_id == "corpus:hr/leave.md"

    def test_something_a_person_can_read(self):
        assert self._one().title == "leave"

    def test_which_scope_it_came_from(self):
        assert self._one().scope == "agent"

    def test_a_document_with_no_title_still_has_something_to_show(self):
        bare = Document(
            id="corpus:x.md",
            text="Claims over 750 require a receipt.",
            scope=Scope.AGENT,
        )
        found = cite(answer="Claims over 750 require a receipt.", found=_found(bare))
        assert found[0].title


class TestTheShapeTheInterfaceReads:
    def test_it_renders_as_plain_data(self):
        import json

        answer = "Staff accrue 25 days of annual leave per year."
        found = cite(answer=answer, found=_found(LEAVE))
        assert json.loads(json.dumps([c.as_dict() for c in found]))

    def test_every_field_the_interface_needs_is_there(self):
        answer = "Staff accrue 25 days of annual leave per year."
        found = cite(answer=answer, found=_found(LEAVE))[0].as_dict()
        assert set(found) >= {"document_id", "title", "scope"}


class TestNotCitingTheSameThingTwice:
    def test_one_document_is_named_once(self):
        answer = (
            "Staff accrue 25 days of annual leave per year. "
            "Staff accrue 25 days of annual leave per year."
        )
        found = cite(answer=answer, found=_found(LEAVE, LEAVE))
        assert len(found) == 1
