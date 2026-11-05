"""A note can be changed after it is written."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from agent.aegra import knowledge_routes
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore


@pytest.fixture
def store() -> InMemoryStore:
    kept = InMemoryStore()
    kept.add(
        Document(
            id="user:1",
            text="the original text",
            scope=Scope.USER,
            owner="someone",
            title="My note",
        )
    )
    kept.add(
        Document(
            id="user:2",
            text="not yours",
            scope=Scope.USER,
            owner="somebody-else",
            title="Theirs",
        )
    )
    kept.add(
        Document(
            id="corpus:policy",
            text="from the configuration tree",
            scope=Scope.AGENT,
            title="Policy",
        )
    )
    return kept


def _viewer(subject: str = "someone") -> Viewer:
    return Viewer(subject=subject, teams=(), thread_id=None)


class TestChangingYourOwnNote:
    def test_the_text_is_replaced(self, store):
        knowledge_routes.rewrite_document(
            store=store,
            viewer=_viewer(),
            document_id="user:1",
            text="the new text",
            title="My note",
            limit=10_000,
        )
        assert store.get("user:1", viewer=_viewer()).text == "the new text"

    def test_the_title_can_change_too(self, store):
        knowledge_routes.rewrite_document(
            store=store,
            viewer=_viewer(),
            document_id="user:1",
            text="x",
            title="A better name",
            limit=10_000,
        )
        assert store.get("user:1", viewer=_viewer()).title == "A better name"

    def test_it_keeps_its_id(self, store):
        knowledge_routes.rewrite_document(
            store=store,
            viewer=_viewer(),
            document_id="user:1",
            text="x",
            title="t",
            limit=10_000,
        )
        assert store.get("user:1", viewer=_viewer()) is not None

    def test_it_stays_yours(self, store):
        knowledge_routes.rewrite_document(
            store=store,
            viewer=_viewer(),
            document_id="user:1",
            text="x",
            title="t",
            limit=10_000,
        )
        assert store.get("user:1", viewer=_viewer()).owner == "someone"


class TestSomebodyElsesNote:
    def test_it_cannot_be_rewritten(self, store):
        with pytest.raises(HTTPException) as refused:
            knowledge_routes.rewrite_document(
                store=store,
                viewer=_viewer(),
                document_id="user:2",
                text="mine now",
                title="t",
                limit=10_000,
            )
        assert refused.value.status_code in (403, 404)

    def test_and_it_is_left_alone(self, store):
        with pytest.raises(HTTPException):
            knowledge_routes.rewrite_document(
                store=store,
                viewer=_viewer(),
                document_id="user:2",
                text="mine now",
                title="t",
                limit=10_000,
            )
        assert store.get("user:2", viewer=_viewer("somebody-else")).text == "not yours"


class TestTheAgentsOwnCorpus:
    def test_it_is_not_editable_here(self, store):
        with pytest.raises(HTTPException) as refused:
            knowledge_routes.rewrite_document(
                store=store,
                viewer=_viewer(),
                document_id="corpus:policy",
                text="changed",
                title="t",
                limit=10_000,
            )
        assert refused.value.status_code == 403


class TestWhatAnEditCosts:
    def test_growing_past_the_quota_is_refused(self, store):
        with pytest.raises(HTTPException) as refused:
            knowledge_routes.rewrite_document(
                store=store,
                viewer=_viewer(),
                document_id="user:1",
                text="x" * 500,
                title="t",
                limit=100,
            )
        assert refused.value.status_code == 413

    def test_the_old_text_is_not_counted_against_the_new(self, store):
        long_enough = "y" * 60
        knowledge_routes.rewrite_document(
            store=store,
            viewer=_viewer(),
            document_id="user:1",
            text=long_enough,
            title="t",
            limit=100,
        )
        assert store.get("user:1", viewer=_viewer()).text == long_enough

    def test_an_empty_note_is_refused(self, store):
        with pytest.raises(HTTPException):
            knowledge_routes.rewrite_document(
                store=store,
                viewer=_viewer(),
                document_id="user:1",
                text="   ",
                title="t",
                limit=10_000,
            )


class TestANoteThatIsNotThere:
    def test_it_is_a_plain_not_found(self, store):
        with pytest.raises(HTTPException) as refused:
            knowledge_routes.rewrite_document(
                store=store,
                viewer=_viewer(),
                document_id="user:nope",
                text="x",
                title="t",
                limit=10_000,
            )
        assert refused.value.status_code == 404


class TestReadingOneNoteBackToEditIt:
    """The list carries titles and sizes, never bodies."""

    def test_your_own_note_comes_back_whole(self, store):
        found = knowledge_routes.read_one(
            store=store, viewer=_viewer(), document_id="user:1"
        )
        assert found["text"] == "the original text"
        assert found["title"] == "My note"

    def test_somebody_elses_does_not(self, store):
        with pytest.raises(HTTPException) as refused:
            knowledge_routes.read_one(
                store=store, viewer=_viewer(), document_id="user:2"
            )
        assert refused.value.status_code in (403, 404)

    def test_a_shared_document_can_be_read(self, store):
        found = knowledge_routes.read_one(
            store=store, viewer=_viewer(), document_id="corpus:policy"
        )
        assert found["text"] == "from the configuration tree"

    def test_a_shared_document_says_it_cannot_be_changed(self, store):
        found = knowledge_routes.read_one(
            store=store, viewer=_viewer(), document_id="corpus:policy"
        )
        assert found["editable"] is False

    def test_your_own_note_says_it_can(self, store):
        found = knowledge_routes.read_one(
            store=store, viewer=_viewer(), document_id="user:1"
        )
        assert found["editable"] is True

    def test_a_note_that_is_not_there_is_a_plain_not_found(self, store):
        with pytest.raises(HTTPException) as refused:
            knowledge_routes.read_one(
                store=store, viewer=_viewer(), document_id="user:nope"
            )
        assert refused.value.status_code == 404
