"""A file attached to a conversation is a session document."""

from __future__ import annotations

from agent.src.knowledge.attachments import remember_attachment
from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import InMemoryStore

ON = Knowledge(
    enabled=True,
    scopes=(Scope.SESSION, Scope.USER, Scope.AGENT),
    order=(Scope.SESSION, Scope.USER, Scope.AGENT),
    top_k=8,
)
NO_SESSION = Knowledge(
    enabled=True, scopes=(Scope.USER, Scope.AGENT), order=(Scope.AGENT,), top_k=8
)

READER = Viewer(subject="alice", teams=(), thread_id="t1")


def _remembered(store, **kwargs):
    return remember_attachment(
        thread_id=kwargs.pop("thread_id", "t1"),
        filename=kwargs.pop("filename", "report.pdf"),
        path=kwargs.pop("path", "/attachments/report.pdf"),
        text=kwargs.pop("text", "Revenue grew 12 per cent in the third quarter."),
        store=store,
        config=kwargs.pop("config", ON),
    )


class TestWhatBecomesSearchable:
    def test_the_extracted_text_is_findable(self):
        store = InMemoryStore()
        _remembered(store)
        found = store.search("revenue", scope=Scope.SESSION, viewer=READER)
        assert found

    def test_it_belongs_to_the_conversation_it_was_attached_to(self):
        store = InMemoryStore()
        _remembered(store, thread_id="t1")
        other = Viewer(subject="alice", teams=(), thread_id="t2")
        assert store.search("revenue", scope=Scope.SESSION, viewer=other) == []

    def test_the_filename_is_what_a_reader_sees(self):
        store = InMemoryStore()
        _remembered(store)
        found = store.search("revenue", scope=Scope.SESSION, viewer=READER)
        assert found[0].title == "report.pdf"

    def test_the_path_travels_so_the_file_can_still_be_opened(self):
        store = InMemoryStore()
        _remembered(store)
        found = store.search("revenue", scope=Scope.SESSION, viewer=READER)
        assert found[0].metadata.get("path") == "/attachments/report.pdf"

    def test_attaching_the_same_file_again_replaces_it(self):
        store = InMemoryStore()
        _remembered(store, text="first version")
        _remembered(store, text="second version")
        assert len(store.documents_in(scope=Scope.SESSION)) == 1

    def test_and_the_newer_text_is_what_is_found(self):
        store = InMemoryStore()
        _remembered(store, text="first version")
        _remembered(store, text="second version")
        found = store.search("second", scope=Scope.SESSION, viewer=READER)
        assert found


class TestWhatIsNotRemembered:
    def test_a_file_with_no_extracted_text(self):
        store = InMemoryStore()
        _remembered(store, text="")
        assert store.documents_in(scope=Scope.SESSION) == []

    def test_whitespace_is_not_text(self):
        store = InMemoryStore()
        _remembered(store, text="   \n  ")
        assert store.documents_in(scope=Scope.SESSION) == []

    def test_nothing_when_the_library_is_off(self):
        store = InMemoryStore()
        _remembered(store, config=Knowledge())
        assert store.documents_in(scope=Scope.SESSION) == []

    def test_nothing_when_the_deployment_keeps_no_session_documents(self):
        store = InMemoryStore()
        _remembered(store, config=NO_SESSION)
        assert store.documents_in(scope=Scope.SESSION) == []

    def test_nothing_without_a_conversation_to_belong_to(self):
        store = InMemoryStore()
        _remembered(store, thread_id="")
        assert store.documents_in(scope=Scope.SESSION) == []


class TestTheUploadStillSucceeds:
    """The file is written and the person is waiting."""

    def test_a_store_that_fails_does_not_raise(self):
        class _Broken:
            def add(self, document):
                raise ConnectionError("store unavailable")

        _remembered(_Broken())

    def test_it_says_whether_it_managed_to(self):
        assert _remembered(InMemoryStore()) is True

    def test_and_says_so_when_it_did_not(self):
        class _Broken:
            def add(self, document):
                raise ConnectionError("store unavailable")

        assert _remembered(_Broken()) is False


class TestTheUploadPathUsesIt:
    def test_the_route_reaches_for_it(self):
        import inspect

        from agent.aegra import attachment_routes

        assert "remember_attachment" in inspect.getsource(attachment_routes)
