"""How much one person may keep in the library."""

from __future__ import annotations

import pytest

from agent.src.knowledge.quota import QuotaExceeded, check_room_for, stored_bytes
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore

ALICE = Viewer(subject="alice", teams=(), thread_id="t1")
BOB = Viewer(subject="bob", teams=(), thread_id="t2")


def _store(**sizes: int) -> InMemoryStore:
    store = InMemoryStore()
    for owner, size in sizes.items():
        store.add(
            Document(id=f"{owner}-1", text="x" * size, scope=Scope.USER, owner=owner)
        )
    return store


class TestWhatIsAlreadyStored:
    def test_nothing_stored_is_nothing(self):
        assert stored_bytes(InMemoryStore(), owner="alice") == 0

    def test_it_counts_what_is_there(self):
        assert stored_bytes(_store(alice=100), owner="alice") == 100

    def test_it_counts_only_this_person(self):
        assert stored_bytes(_store(alice=100, bob=900), owner="alice") == 100

    def test_it_does_not_count_the_curated_corpus(self):
        store = _store(alice=100)
        store.add(Document(id="a1", text="y" * 500, scope=Scope.AGENT))
        assert stored_bytes(store, owner="alice") == 100

    def test_it_does_not_count_conversation_attachments(self):
        store = _store(alice=100)
        store.add(
            Document(id="s1", text="y" * 500, scope=Scope.SESSION, thread_id="t1")
        )
        assert stored_bytes(store, owner="alice") == 100

    def test_it_counts_in_bytes_not_characters(self):
        store = InMemoryStore()
        store.add(Document(id="a", text="é" * 10, scope=Scope.USER, owner="alice"))
        assert stored_bytes(store, owner="alice") == 20


class TestWhetherThereIsRoom:
    def test_a_small_document_fits(self):
        assert (
            check_room_for(10, store=_store(alice=100), owner="alice", limit=1000)
            is None
        )

    def test_one_that_would_not_fit_is_refused(self):
        with pytest.raises(QuotaExceeded):
            check_room_for(950, store=_store(alice=100), owner="alice", limit=1000)

    def test_the_refusal_says_how_much_is_used(self):
        with pytest.raises(QuotaExceeded, match="100"):
            check_room_for(950, store=_store(alice=100), owner="alice", limit=1000)

    def test_the_refusal_says_the_limit(self):
        with pytest.raises(QuotaExceeded, match="1000"):
            check_room_for(950, store=_store(alice=100), owner="alice", limit=1000)

    def test_exactly_filling_it_is_allowed(self):
        assert (
            check_room_for(900, store=_store(alice=100), owner="alice", limit=1000)
            is None
        )

    def test_one_byte_over_is_not(self):
        with pytest.raises(QuotaExceeded):
            check_room_for(901, store=_store(alice=100), owner="alice", limit=1000)

    def test_another_persons_documents_do_not_use_up_the_room(self):
        assert (
            check_room_for(
                900, store=_store(alice=100, bob=5000), owner="alice", limit=1000
            )
            is None
        )

    def test_a_limit_of_zero_refuses_everything(self):
        with pytest.raises(QuotaExceeded):
            check_room_for(1, store=InMemoryStore(), owner="alice", limit=0)

    def test_an_empty_document_is_refused_before_the_quota_is_consulted(self):
        with pytest.raises(ValueError):
            check_room_for(0, store=InMemoryStore(), owner="alice", limit=1000)
