"""A document is reachable through a scope, and the scope is the query."""

from __future__ import annotations

import pytest

from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore, ScopeViolation

ALICE = Viewer(subject="alice", teams=(), thread_id="t1")
BOB = Viewer(subject="bob", teams=(), thread_id="t2")


def _seeded() -> InMemoryStore:
    """One document in every scope, all saying the same thing."""
    store = InMemoryStore()
    store.add(
        Document(id="s1", text="the limit is 750", scope=Scope.SESSION, thread_id="t1")
    )
    store.add(
        Document(id="u1", text="the limit is 750", scope=Scope.USER, owner="alice")
    )
    store.add(Document(id="a1", text="the limit is 750", scope=Scope.AGENT))
    store.add(Document(id="u2", text="the limit is 750", scope=Scope.USER, owner="bob"))
    store.add(
        Document(id="s2", text="the limit is 750", scope=Scope.SESSION, thread_id="t2")
    )
    return store


class TestTheScopeIsTheQuery:
    """The guard this epic exists behind."""

    def test_asking_for_session_returns_only_session(self):
        found = _seeded().search("limit", scope=Scope.SESSION, viewer=ALICE)
        assert {d.scope for d in found} == {Scope.SESSION}

    def test_asking_for_user_returns_only_user(self):
        found = _seeded().search("limit", scope=Scope.USER, viewer=ALICE)
        assert {d.scope for d in found} == {Scope.USER}

    def test_asking_for_agent_returns_only_agent(self):
        found = _seeded().search("limit", scope=Scope.AGENT, viewer=ALICE)
        assert {d.scope for d in found} == {Scope.AGENT}

    def test_session_does_not_leak_the_users_document(self):
        found = _seeded().search("limit", scope=Scope.SESSION, viewer=ALICE)
        assert "u1" not in {d.id for d in found}

    def test_session_does_not_leak_the_agents_corpus(self):
        found = _seeded().search("limit", scope=Scope.SESSION, viewer=ALICE)
        assert "a1" not in {d.id for d in found}

    def test_user_does_not_leak_the_agents_corpus(self):
        found = _seeded().search("limit", scope=Scope.USER, viewer=ALICE)
        assert "a1" not in {d.id for d in found}

    def test_agent_does_not_leak_anybodys_own_documents(self):
        found = _seeded().search("limit", scope=Scope.AGENT, viewer=ALICE)
        assert {d.id for d in found} == {"a1"}

    def test_one_scope_at_a_time_and_no_way_to_ask_for_several(self):
        import inspect

        signature = inspect.signature(InMemoryStore.search)
        assert signature.parameters["scope"].annotation in (Scope, "Scope")


class TestWhoseDocumentItIs:
    def test_a_user_sees_their_own(self):
        found = _seeded().search("limit", scope=Scope.USER, viewer=ALICE)
        assert {d.id for d in found} == {"u1"}

    def test_a_user_does_not_see_another_persons(self):
        found = _seeded().search("limit", scope=Scope.USER, viewer=ALICE)
        assert "u2" not in {d.id for d in found}

    def test_the_other_person_sees_only_theirs(self):
        found = _seeded().search("limit", scope=Scope.USER, viewer=BOB)
        assert {d.id for d in found} == {"u2"}

    def test_a_conversation_does_not_see_another_conversations(self):
        found = _seeded().search("limit", scope=Scope.SESSION, viewer=ALICE)
        assert "s2" not in {d.id for d in found}

    def test_a_viewer_in_no_conversation_gets_no_session_documents(self):
        nowhere = Viewer(subject="alice", teams=(), thread_id=None)
        assert _seeded().search("limit", scope=Scope.SESSION, viewer=nowhere) == []


class TestReachingOneByIdentifier:
    """Search is not the only door."""

    def test_a_user_can_fetch_their_own(self):
        assert _seeded().get("u1", viewer=ALICE) is not None

    def test_a_user_cannot_fetch_another_persons(self):
        with pytest.raises(ScopeViolation):
            _seeded().get("u2", viewer=ALICE)

    def test_a_conversation_cannot_fetch_anothers(self):
        with pytest.raises(ScopeViolation):
            _seeded().get("s2", viewer=ALICE)

    def test_anybody_can_fetch_from_the_agents_corpus(self):
        assert _seeded().get("a1", viewer=BOB) is not None

    def test_a_document_that_does_not_exist_is_not_a_violation(self):
        assert _seeded().get("nothing", viewer=ALICE) is None

    def test_a_refusal_does_not_say_what_the_document_was(self):
        try:
            _seeded().get("u2", viewer=ALICE)
        except ScopeViolation as refused:
            assert "750" not in str(refused)


class TestAddingSomethingIncoherent:
    def test_a_user_document_with_no_owner_is_refused(self):
        store = InMemoryStore()
        with pytest.raises(ValueError):
            store.add(Document(id="x", text="t", scope=Scope.USER))

    def test_a_session_document_with_no_conversation_is_refused(self):
        store = InMemoryStore()
        with pytest.raises(ValueError):
            store.add(Document(id="x", text="t", scope=Scope.SESSION))

    def test_an_agent_document_with_an_owner_is_refused(self):
        store = InMemoryStore()
        with pytest.raises(ValueError):
            store.add(Document(id="x", text="t", scope=Scope.AGENT, owner="alice"))


class TestRemoving:
    def test_a_document_can_be_removed(self):
        store = _seeded()
        store.remove("u1", viewer=ALICE)
        assert store.get("u1", viewer=ALICE) is None

    def test_one_person_cannot_remove_anothers(self):
        store = _seeded()
        with pytest.raises(ScopeViolation):
            store.remove("u2", viewer=ALICE)

    def test_and_it_is_still_there_afterwards(self):
        store = _seeded()
        with pytest.raises(ScopeViolation):
            store.remove("u2", viewer=ALICE)
        assert store.get("u2", viewer=BOB) is not None

    def test_removing_a_conversation_takes_its_documents(self):
        store = _seeded()
        store.forget_thread("t1")
        assert store.search("limit", scope=Scope.SESSION, viewer=ALICE) == []

    def test_it_leaves_other_conversations_alone(self):
        store = _seeded()
        store.forget_thread("t1")
        assert store.search("limit", scope=Scope.SESSION, viewer=BOB)

    def test_it_leaves_the_users_own_documents_alone(self):
        store = _seeded()
        store.forget_thread("t1")
        assert store.search("limit", scope=Scope.USER, viewer=ALICE)


class TestWhatAResultCarries:
    def test_it_says_which_scope_it_came_from(self):
        found = _seeded().search("limit", scope=Scope.AGENT, viewer=ALICE)
        assert found[0].scope is Scope.AGENT

    def test_it_says_which_document(self):
        found = _seeded().search("limit", scope=Scope.AGENT, viewer=ALICE)
        assert found[0].id == "a1"


class TestHowManyComeBack:
    def test_the_caller_can_cap_it(self):
        store = InMemoryStore()
        for i in range(10):
            store.add(Document(id=f"a{i}", text="limit", scope=Scope.AGENT))
        assert len(store.search("limit", scope=Scope.AGENT, viewer=ALICE, top_k=3)) == 3

    def test_nothing_matching_is_an_empty_answer_not_an_error(self):
        assert _seeded().search("zebra", scope=Scope.AGENT, viewer=ALICE) == []


class TestEveryScopeTheStoreNamesIsReachable:
    """A scope that exists and can never return anything reads"""

    def test_each_kept_scope_can_be_searched(self):
        from agent.src.knowledge.store import KEPT

        store = _seeded()
        for scope in KEPT:
            store.search("limit", scope=scope, viewer=ALICE)

    def test_the_enum_holds_nothing_the_store_refuses(self):
        from agent.src.knowledge.store import KEPT

        assert set(Scope) == set(KEPT)


class TestForgettingACorpusTheTreeNoLongerHas:
    """Ingestion is a sync, so the store has to be able to drop"""

    def _corpus(self):
        store = InMemoryStore()
        store.add(Document(id="corpus:a.md", text="policy one", scope=Scope.AGENT))
        store.add(Document(id="corpus:b.md", text="policy two", scope=Scope.AGENT))
        store.add(Document(id="elsewhere", text="policy three", scope=Scope.AGENT))
        store.add(
            Document(id="u1", text="policy mine", scope=Scope.USER, owner="alice")
        )
        return store

    def test_a_departed_document_goes(self):
        store = self._corpus()
        store.forget_corpus(prefix="corpus:", keeping={"corpus:a.md"})
        assert store.get("corpus:b.md", viewer=ALICE) is None

    def test_the_one_still_there_stays(self):
        store = self._corpus()
        store.forget_corpus(prefix="corpus:", keeping={"corpus:a.md"})
        assert store.get("corpus:a.md", viewer=ALICE) is not None

    def test_it_counts_what_it_removed(self):
        store = self._corpus()
        assert store.forget_corpus(prefix="corpus:", keeping=set()) == 2

    def test_it_leaves_documents_another_corpus_put_there(self):
        store = self._corpus()
        store.forget_corpus(prefix="corpus:", keeping=set())
        assert store.get("elsewhere", viewer=ALICE) is not None

    def test_it_leaves_personal_documents_alone(self):
        store = self._corpus()
        store.forget_corpus(prefix="corpus:", keeping=set())
        assert store.get("u1", viewer=ALICE) is not None


class TestForgettingReachesEveryScopeACorpusWrites:
    """A corpus writes to the shared scope and to team scopes."""

    def _both(self):
        store = InMemoryStore()
        store.add(Document(id="corpus:a.md", text="shared", scope=Scope.AGENT))
        store.add(
            Document(
                id="corpus:teams/platform/b.md",
                text="theirs",
                scope=Scope.TEAM,
                team="platform",
            )
        )
        return store

    def test_a_departed_team_document_goes_too(self):
        store = self._both()
        store.forget_corpus(prefix="corpus:", keeping={"corpus:a.md"})
        member = Viewer(subject="amar", teams=("platform",), thread_id=None)
        assert store.search("theirs", scope=Scope.TEAM, viewer=member) == []

    def test_the_shared_one_that_remains_is_untouched(self):
        store = self._both()
        store.forget_corpus(prefix="corpus:", keeping={"corpus:a.md"})
        assert store.get("corpus:a.md", viewer=ALICE) is not None

    def test_it_counts_both(self):
        assert self._both().forget_corpus(prefix="corpus:", keeping=set()) == 2
