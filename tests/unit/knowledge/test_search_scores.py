"""How well a document matched, not merely that it did."""

from __future__ import annotations

from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore

ALICE = Viewer(subject="alice", teams=(), thread_id="t1")


def _store():
    store = InMemoryStore()
    store.add(
        Document(
            id="both",
            text="the daily spend limit refuses a run",
            scope=Scope.USER,
            owner="alice",
            title="Both",
        )
    )
    store.add(
        Document(
            id="one",
            text="a limit on something else entirely",
            scope=Scope.USER,
            owner="alice",
            title="One",
        )
    )
    return store


class TestTheScore:
    def test_a_hit_carries_one(self):
        found = _store().search_scored("daily spend", scope=Scope.USER, viewer=ALICE)
        assert found[0].score > 0

    def test_every_word_matching_scores_one(self):
        found = _store().search_scored("daily spend", scope=Scope.USER, viewer=ALICE)
        assert found[0].score == 1.0

    def test_half_the_words_matching_scores_half(self):
        found = _store().search_scored("limit nowhere", scope=Scope.USER, viewer=ALICE)
        assert all(hit.score == 0.5 for hit in found)

    def test_a_document_matching_nothing_is_not_a_hit(self):
        found = _store().search_scored("pelican", scope=Scope.USER, viewer=ALICE)
        assert found == []

    def test_the_document_comes_with_it(self):
        found = _store().search_scored("daily spend", scope=Scope.USER, viewer=ALICE)
        assert found[0].document.id == "both"


class TestRanking:
    def test_the_better_match_comes_first(self):
        found = _store().search_scored(
            "daily spend limit", scope=Scope.USER, viewer=ALICE
        )
        assert [hit.document.id for hit in found] == ["both", "one"]

    def test_the_cap_keeps_the_best_rather_than_the_first(self):
        found = _store().search_scored(
            "daily spend limit", scope=Scope.USER, viewer=ALICE, top_k=1
        )
        assert [hit.document.id for hit in found] == ["both"]


class TestTheOlderWayStillWorks:
    def test_it_returns_documents(self):
        found = _store().search("limit", scope=Scope.USER, viewer=ALICE)
        assert all(isinstance(document, Document) for document in found)

    def test_it_is_ranked_too(self):
        found = _store().search("daily spend limit", scope=Scope.USER, viewer=ALICE)
        assert [document.id for document in found] == ["both", "one"]

    def test_scope_is_still_enforced(self):
        found = _store().search("limit", scope=Scope.AGENT, viewer=ALICE)
        assert found == []

    def test_somebody_elses_documents_are_still_out_of_reach(self):
        found = _store().search(
            "limit",
            scope=Scope.USER,
            viewer=Viewer(subject="bob", teams=(), thread_id="t1"),
        )
        assert found == []
