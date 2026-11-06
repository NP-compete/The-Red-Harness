"""An error code in a document is findable by that error code."""

from __future__ import annotations

import pytest

from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore


@pytest.fixture
def store() -> InMemoryStore:
    kept = InMemoryStore()
    kept.add(
        Document(
            id="runbook",
            text="If the gateway returns ERR-4021, restart the pool.",
            scope=Scope.AGENT,
            title="runbook",
        )
    )
    kept.add(
        Document(
            id="pricing",
            text="Plans are billed monthly (see the account_id field).",
            scope=Scope.AGENT,
            title="pricing",
        )
    )
    return kept


def _viewer() -> Viewer:
    return Viewer(subject="someone", teams=(), thread_id=None)


def _found(store: InMemoryStore, query: str) -> list[str]:
    return [
        hit.document.id
        for hit in store.search_scored(query, scope=Scope.AGENT, viewer=_viewer())
    ]


class TestATermTouchingPunctuation:
    def test_a_code_before_a_comma_is_found(self, store):
        assert "runbook" in _found(store, "ERR-4021")

    def test_a_field_name_inside_brackets_is_found(self, store):
        assert "pricing" in _found(store, "account_id")

    def test_a_word_before_a_full_stop_is_found(self, store):
        assert "runbook" in _found(store, "pool")

    def test_case_still_does_not_matter(self, store):
        assert "runbook" in _found(store, "err-4021")


class TestItDidNotGetLooser:
    def test_a_term_that_is_absent_is_still_absent(self, store):
        assert _found(store, "ERR-9999") == []

    def test_a_fragment_of_a_term_does_not_match_it(self, store):
        assert _found(store, "4021") == []

    def test_an_empty_question_still_matches_nothing(self, store):
        assert _found(store, "   ") == []

    def test_the_better_match_still_ranks_first(self, store):
        hits = store.search_scored(
            "ERR-4021 gateway pool", scope=Scope.AGENT, viewer=_viewer()
        )
        assert hits and hits[0].document.id == "runbook"


class TestTheScoreStillMakesSense:
    def test_it_is_the_fraction_of_the_question_that_matched(self, store):
        hits = store.search_scored("ERR-4021", scope=Scope.AGENT, viewer=_viewer())
        assert hits[0].score == pytest.approx(1.0)

    def test_half_a_question_scores_half(self, store):
        hits = store.search_scored(
            "ERR-4021 unrelatedword", scope=Scope.AGENT, viewer=_viewer()
        )
        assert hits[0].score == pytest.approx(0.5)
