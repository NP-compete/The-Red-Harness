"""Asking the library a question, on behalf of a turn."""

from __future__ import annotations

import pytest

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.retrieval import RetrievalRefused, retrieve
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore

ALICE = Viewer(subject="alice", teams=(), thread_id="t1")

ALL_ON = Knowledge(
    enabled=True,
    scopes=(Scope.SESSION, Scope.USER, Scope.AGENT),
    order=(Scope.SESSION, Scope.USER, Scope.AGENT),
    top_k=8,
)


def _store(*, session=False, user=False, agent=False) -> InMemoryStore:
    store = InMemoryStore()
    if session:
        store.add(
            Document(
                id="s1", text="the limit is 750", scope=Scope.SESSION, thread_id="t1"
            )
        )
    if user:
        store.add(
            Document(id="u1", text="the limit is 750", scope=Scope.USER, owner="alice")
        )
    if agent:
        store.add(Document(id="a1", text="the limit is 750", scope=Scope.AGENT))
    return store


class TestWhenTheModelNamesAScope:
    def test_it_searches_that_one(self):
        found = retrieve(
            "limit",
            scope=Scope.AGENT,
            store=_store(agent=True),
            viewer=ALICE,
            config=ALL_ON,
        )
        assert [d.id for d in found.documents] == ["a1"]

    def test_it_searches_no_other(self):
        found = retrieve(
            "limit",
            scope=Scope.AGENT,
            store=_store(session=True, agent=True),
            viewer=ALICE,
            config=ALL_ON,
        )
        assert [d.id for d in found.documents] == ["a1"]

    def test_an_empty_scope_answers_nothing_rather_than_falling_through(self):
        found = retrieve(
            "limit",
            scope=Scope.USER,
            store=_store(session=True, agent=True),
            viewer=ALICE,
            config=ALL_ON,
        )
        assert found.documents == []

    def test_a_scope_this_deployment_turned_off_is_refused(self):
        narrowed = Knowledge(
            enabled=True, scopes=(Scope.AGENT,), order=(Scope.AGENT,), top_k=8
        )
        with pytest.raises(RetrievalRefused, match="user"):
            retrieve(
                "limit",
                scope=Scope.USER,
                store=_store(user=True),
                viewer=ALICE,
                config=narrowed,
            )


class TestWhenNobodyNamesOne:
    def test_the_narrowest_that_answers_wins(self):
        found = retrieve(
            "limit",
            store=_store(session=True, user=True, agent=True),
            viewer=ALICE,
            config=ALL_ON,
        )
        assert [d.id for d in found.documents] == ["s1"]

    def test_it_moves_outward_when_the_narrow_one_is_empty(self):
        found = retrieve(
            "limit", store=_store(user=True, agent=True), viewer=ALICE, config=ALL_ON
        )
        assert [d.id for d in found.documents] == ["u1"]

    def test_and_outward_again(self):
        found = retrieve("limit", store=_store(agent=True), viewer=ALICE, config=ALL_ON)
        assert [d.id for d in found.documents] == ["a1"]

    def test_it_stops_rather_than_merging(self):
        found = retrieve(
            "limit",
            store=_store(session=True, user=True, agent=True),
            viewer=ALICE,
            config=ALL_ON,
        )
        assert len({d.scope for d in found.documents}) == 1

    def test_nothing_anywhere_is_an_empty_answer(self):
        found = retrieve("limit", store=_store(), viewer=ALICE, config=ALL_ON)
        assert found.documents == []

    def test_it_follows_the_order_the_deployment_set(self):
        widest_first = Knowledge(
            enabled=True,
            scopes=(Scope.SESSION, Scope.USER, Scope.AGENT),
            order=(Scope.AGENT, Scope.SESSION),
            top_k=8,
        )
        found = retrieve(
            "limit",
            store=_store(session=True, agent=True),
            viewer=ALICE,
            config=widest_first,
        )
        assert [d.id for d in found.documents] == ["a1"]

    def test_it_never_walks_into_a_scope_that_is_off(self):
        narrowed = Knowledge(
            enabled=True, scopes=(Scope.AGENT,), order=(Scope.AGENT,), top_k=8
        )
        found = retrieve(
            "limit", store=_store(user=True, agent=True), viewer=ALICE, config=narrowed
        )
        assert [d.id for d in found.documents] == ["a1"]


class TestWhatComesBack:
    def test_it_says_which_scope_answered(self):
        found = retrieve("limit", store=_store(agent=True), viewer=ALICE, config=ALL_ON)
        assert found.scope is Scope.AGENT

    def test_it_says_which_scope_answered_even_when_nothing_did(self):
        found = retrieve("limit", store=_store(), viewer=ALICE, config=ALL_ON)
        assert found.scope is None

    def test_each_document_carries_its_own_scope(self):
        found = retrieve("limit", store=_store(agent=True), viewer=ALICE, config=ALL_ON)
        assert found.documents[0].scope is Scope.AGENT

    def test_each_document_carries_its_identifier(self):
        found = retrieve("limit", store=_store(agent=True), viewer=ALICE, config=ALL_ON)
        assert found.documents[0].id == "a1"

    def test_it_says_which_scopes_it_tried(self):
        found = retrieve("limit", store=_store(), viewer=ALICE, config=ALL_ON)
        assert found.searched == (Scope.SESSION, Scope.USER, Scope.AGENT)


class TestWhenTheLibraryIsOff:
    OFF = Knowledge(enabled=False)

    def test_asking_is_refused_rather_than_answered_emptily(self):
        with pytest.raises(RetrievalRefused):
            retrieve("limit", store=_store(agent=True), viewer=ALICE, config=self.OFF)

    def test_the_refusal_says_the_library_is_off(self):
        with pytest.raises(RetrievalRefused, match="not enabled"):
            retrieve("limit", store=_store(agent=True), viewer=ALICE, config=self.OFF)


class TestHowMuchComesBack:
    def test_the_configured_cap_applies(self):
        store = InMemoryStore()
        for i in range(10):
            store.add(Document(id=f"a{i}", text="limit", scope=Scope.AGENT))
        tight = Knowledge(
            enabled=True, scopes=(Scope.AGENT,), order=(Scope.AGENT,), top_k=3
        )
        found = retrieve("limit", store=store, viewer=ALICE, config=tight)
        assert len(found.documents) == 3


class TestAnEmptyQuestion:
    @pytest.mark.parametrize("question", ["", "   "])
    def test_it_is_refused(self, question):
        with pytest.raises(RetrievalRefused):
            retrieve(question, store=_store(agent=True), viewer=ALICE, config=ALL_ON)
