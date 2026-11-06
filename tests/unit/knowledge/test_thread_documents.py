"""A deleted conversation takes its documents with it."""

from __future__ import annotations

import pytest

from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore

ALICE = Viewer(subject="alice", teams=(), thread_id="t1")
BOB = Viewer(subject="bob", teams=(), thread_id="t2")


def _store() -> InMemoryStore:
    store = InMemoryStore()
    store.add(Document(id="s1", text="a file", scope=Scope.SESSION, thread_id="t1"))
    store.add(Document(id="s2", text="a file", scope=Scope.SESSION, thread_id="t2"))
    store.add(Document(id="u1", text="a file", scope=Scope.USER, owner="alice"))
    store.add(Document(id="a1", text="a file", scope=Scope.AGENT))
    return store


class TestForgettingAConversation:
    def test_its_documents_go(self):
        store = _store()
        store.forget_thread("t1")
        assert store.search("file", scope=Scope.SESSION, viewer=ALICE) == []

    def test_another_conversations_stay(self):
        store = _store()
        store.forget_thread("t1")
        assert store.search("file", scope=Scope.SESSION, viewer=BOB)

    def test_the_owners_own_documents_stay(self):
        store = _store()
        store.forget_thread("t1")
        assert store.search("file", scope=Scope.USER, viewer=ALICE)

    def test_the_curated_corpus_stays(self):
        store = _store()
        store.forget_thread("t1")
        assert store.search("file", scope=Scope.AGENT, viewer=ALICE)

    def test_forgetting_a_conversation_that_had_none_is_harmless(self):
        store = _store()
        store.forget_thread("never-existed")
        assert store.get("s1", viewer=ALICE) is not None


class TestTheDeletionPathCallsIt:
    """A store that can forget and nothing that asks it to is the"""

    def test_the_cleanup_module_reaches_for_it(self):
        import inspect

        from agent.aegra import thread_cleanup

        assert "forget_thread" in inspect.getsource(thread_cleanup)

    @pytest.mark.asyncio
    async def test_a_store_that_fails_does_not_fail_the_deletion(self):
        from agent.aegra.thread_cleanup import _forget_thread_documents

        class _Broken:
            def forget_thread(self, thread_id):
                raise ConnectionError("store unavailable")

        await _forget_thread_documents("t1", store=_Broken())

    @pytest.mark.asyncio
    async def test_it_asks_the_store_to_forget_the_thread(self):
        from agent.aegra.thread_cleanup import _forget_thread_documents

        asked = []

        class _Spy:
            def forget_thread(self, thread_id):
                asked.append(thread_id)

        await _forget_thread_documents("t1", store=_Spy())
        assert asked == ["t1"]

    @pytest.mark.asyncio
    async def test_it_does_nothing_when_the_library_is_off(self):
        from agent.aegra.thread_cleanup import _forget_thread_documents

        await _forget_thread_documents("t1", store=None)
