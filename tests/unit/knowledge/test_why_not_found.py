"""Why a document was not used."""

from __future__ import annotations

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.retrieval import retrieve
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore

ALICE = Viewer(subject="alice", teams=(), thread_id="t1")


def _config(**kwargs):
    return Knowledge(
        enabled=True,
        scopes=(Scope.USER,),
        order=(Scope.USER,),
        top_k=kwargs.pop("top_k", 8),
        min_score=kwargs.pop("min_score", 0.0),
    )


def _store():
    store = InMemoryStore()
    store.add(
        Document(
            id="strong",
            text="the daily spend limit refuses a run",
            scope=Scope.USER,
            owner="alice",
            title="Strong",
        )
    )
    store.add(
        Document(
            id="weak",
            text="a limit on something else entirely",
            scope=Scope.USER,
            owner="alice",
            title="Weak",
        )
    )
    return store


def _found(**kwargs):
    return retrieve(
        kwargs.pop("question", "daily spend limit"),
        store=_store(),
        viewer=ALICE,
        config=_config(**kwargs),
    )


class TestTheThresholdFinallyApplies:
    def test_a_weak_match_is_dropped(self):
        found = _found(min_score=0.5)
        assert [document.id for document in found.documents] == ["strong"]

    def test_a_strong_match_is_kept(self):
        assert _found(min_score=0.5).documents

    def test_no_threshold_keeps_everything(self):
        assert len(_found(min_score=0.0).documents) == 2

    def test_a_threshold_nothing_meets_finds_nothing(self):
        assert _found(min_score=0.99, question="daily limit nowhere").documents == []

    def test_the_scope_is_not_claimed_when_nothing_survives(self):
        assert _found(min_score=0.99, question="daily limit nowhere").scope is None


class TestWhatItNearlyUsed:
    def test_the_kept_documents_carry_their_scores(self):
        found = _found()
        assert all(hit.score > 0 for hit in found.hits)

    def test_the_best_is_first(self):
        assert _found().hits[0].document.id == "strong"

    def test_a_document_the_threshold_dropped_is_recorded(self):
        found = _found(min_score=0.5)
        assert [hit.document.id for hit in found.below_threshold] == ["weak"]

    def test_the_dropped_document_keeps_its_score(self):
        found = _found(min_score=0.5)
        assert 0 < found.below_threshold[0].score < 0.5

    def test_nothing_is_dropped_when_there_is_no_threshold(self):
        assert _found(min_score=0.0).below_threshold == ()

    def test_a_document_sharing_no_words_is_not_a_near_miss(self):
        found = _found(question="pelican", min_score=0.5)
        assert found.below_threshold == ()

    def test_the_cap_is_applied_to_what_survives(self):
        found = _found(top_k=1)
        assert len(found.documents) == 1


class TestWhatWasSearchedIsStillSaid:
    def test_the_scopes_tried_are_reported(self):
        assert _found().searched == (Scope.USER,)

    def test_the_answering_scope_is_reported(self):
        assert _found().scope is Scope.USER
