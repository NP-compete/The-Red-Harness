"""A long document is searchable, not skipped."""

from __future__ import annotations

import pathlib

import pytest

from agent.src.knowledge.ingest import sync_corpus
from agent.src.knowledge.store import Document, Scope


class _Store:
    """Enough of a store to see what was written."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    def add(self, document: Document) -> None:
        self.documents[document.id] = document

    def forget_corpus(self, *, prefix: str, keeping: set[str]) -> int:
        stale = [
            key
            for key in self.documents
            if key.startswith(prefix) and key not in keeping
        ]
        for key in stale:
            del self.documents[key]
        return len(stale)


@pytest.fixture
def corpus(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "corpus"
    root.mkdir()
    return root


def _write(root: pathlib.Path, name: str, text: str) -> None:
    (root / name).write_text(text, encoding="utf-8")


class TestASmallDocumentIsUnchanged:
    def test_it_is_stored_whole(self, corpus):
        _write(corpus, "note.md", "a short note about pricing")
        store = _Store()
        found = sync_corpus(corpus, store=store)

        assert found.ingested == 1
        assert len(store.documents) == 1
        assert "a short note about pricing" in next(iter(store.documents.values())).text

    def test_its_id_gains_no_suffix(self, corpus):
        _write(corpus, "note.md", "a short note")
        store = _Store()
        sync_corpus(corpus, store=store)
        assert not any("#" in key for key in store.documents)


class TestALongDocumentIsSplit:
    def _long(self) -> str:
        return "\n\n".join(f"Paragraph {n} about topic {n}." for n in range(400))

    def test_it_is_not_skipped(self, corpus):
        _write(corpus, "report.md", self._long())
        store = _Store()
        found = sync_corpus(corpus, store=store, max_bytes=2048)

        assert found.skipped == []
        assert store.documents, "a long document reached the corpus as nothing"

    def test_it_arrives_as_several_parts(self, corpus):
        _write(corpus, "report.md", self._long())
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        assert len(store.documents) > 1

    def test_every_part_keeps_the_document_title(self, corpus):
        _write(corpus, "report.md", self._long())
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        assert {d.title for d in store.documents.values()} == {"report"}

    def test_every_part_keeps_the_scope(self, corpus):
        _write(corpus, "report.md", self._long())
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        assert {d.scope for d in store.documents.values()} == {Scope.AGENT}

    def test_the_whole_text_is_present_across_the_parts(self, corpus):
        _write(corpus, "report.md", self._long())
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        joined = " ".join(d.text for d in store.documents.values())
        assert "Paragraph 0 " in joined
        assert "Paragraph 399 " in joined

    def test_each_part_says_which_file_it_came_from(self, corpus):
        _write(corpus, "report.md", self._long())
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        for document in store.documents.values():
            assert document.metadata.get("path", "").endswith("report.md")


class TestResyncing:
    def test_parts_of_a_shrunken_file_are_forgotten(self, corpus):
        long_text = "\n\n".join(f"Paragraph {n}." for n in range(400))
        _write(corpus, "report.md", long_text)
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        many = len(store.documents)
        assert many > 1

        _write(corpus, "report.md", "just this now")
        sync_corpus(corpus, store=store, max_bytes=2048)
        assert len(store.documents) == 1
        assert "just this now" in next(iter(store.documents.values())).text

    def test_a_deleted_file_leaves_nothing_behind(self, corpus):
        _write(corpus, "report.md", "\n\n".join(f"Paragraph {n}." for n in range(400)))
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        (corpus / "report.md").unlink()
        sync_corpus(corpus, store=store, max_bytes=2048)
        assert store.documents == {}


class TestThereIsStillALimit:
    """Splitting is not a licence to ingest anything."""

    def test_an_enormous_file_is_capped_rather_than_refused(self, corpus):
        _write(corpus, "huge.md", "\n\n".join(f"Paragraph {n}." for n in range(20000)))
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=512)

        assert store.documents, "an enormous document reached the corpus as nothing"
        assert len(store.documents) <= 200

    def test_being_capped_is_said_rather_than_silent(self, corpus):
        _write(corpus, "huge.md", "\n\n".join(f"Paragraph {n}." for n in range(20000)))
        store = _Store()
        found = sync_corpus(corpus, store=store, max_bytes=512)

        assert any("huge.md" in reason for reason in found.skipped)
        assert any("part" in reason.lower() for reason in found.skipped)

    def test_what_was_kept_is_the_beginning(self, corpus):
        _write(corpus, "huge.md", "\n\n".join(f"Paragraph {n}." for n in range(20000)))
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=512)
        joined = " ".join(d.text for d in store.documents.values())
        assert "Paragraph 0." in joined
