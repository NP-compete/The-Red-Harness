"""How a corpus is cut up, as a setting rather than a constant."""

from __future__ import annotations

import pathlib

import pytest

from agent.src.knowledge.config import KnowledgeMisconfigured, read_knowledge
from agent.src.knowledge.ingest import sync_corpus
from agent.src.knowledge.store import Document


class _Store:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    def add(self, document: Document) -> None:
        self.documents[document.id] = document

    def forget_corpus(self, *, prefix: str, keeping: set[str]) -> int:
        stale = [k for k in self.documents if k.startswith(prefix) and k not in keeping]
        for key in stale:
            del self.documents[key]
        return len(stale)


@pytest.fixture
def corpus(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "report.md").write_text(
        "\n\n".join(f"Paragraph {n} of the report." for n in range(400)),
        encoding="utf-8",
    )
    return root


class TestTheDefaultIsUnchanged:
    def test_an_existing_corpus_chunks_as_it_did(self, corpus):
        store = _Store()
        sync_corpus(corpus, store=store, max_bytes=2048)
        before = len(store.documents)

        other = _Store()
        sync_corpus(
            corpus, store=other, max_bytes=2048, chunk_size=1200, chunk_overlap=200
        )
        assert len(other.documents) == before

    def test_the_configuration_default_matches_the_code_default(self):
        settings = read_knowledge(
            {"knowledge": {"enabled": True, "scopes": {"agent": True}}}
        )
        assert settings.chunk_size == 1200
        assert settings.chunk_overlap == 200


class TestItCanBeChanged:
    def test_a_smaller_chunk_yields_more_parts(self, corpus):
        store = _Store()
        sync_corpus(
            corpus, store=store, max_bytes=2048, chunk_size=400, chunk_overlap=50
        )
        many = len(store.documents)

        other = _Store()
        sync_corpus(
            corpus, store=other, max_bytes=2048, chunk_size=4000, chunk_overlap=50
        )
        assert many > len(other.documents)

    def test_it_is_read_from_configuration(self):
        settings = read_knowledge(
            {
                "knowledge": {
                    "enabled": True,
                    "scopes": {"agent": True},
                    "retrieval": {"chunk_size": 800, "chunk_overlap": 100},
                }
            }
        )
        assert settings.chunk_size == 800
        assert settings.chunk_overlap == 100


class TestASettingThatWouldBreakRetrieval:
    def test_a_chunk_of_nothing_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured):
            read_knowledge(
                {
                    "knowledge": {
                        "enabled": True,
                        "scopes": {"agent": True},
                        "retrieval": {"chunk_size": 0},
                    }
                }
            )

    def test_words_are_refused_where_a_number_belongs(self):
        with pytest.raises(KnowledgeMisconfigured):
            read_knowledge(
                {
                    "knowledge": {
                        "enabled": True,
                        "scopes": {"agent": True},
                        "retrieval": {"chunk_size": "big"},
                    }
                }
            )

    def test_an_overlap_as_large_as_the_chunk_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured):
            read_knowledge(
                {
                    "knowledge": {
                        "enabled": True,
                        "scopes": {"agent": True},
                        "retrieval": {"chunk_size": 500, "chunk_overlap": 500},
                    }
                }
            )

    def test_a_negative_overlap_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured):
            read_knowledge(
                {
                    "knowledge": {
                        "enabled": True,
                        "scopes": {"agent": True},
                        "retrieval": {"chunk_overlap": -1},
                    }
                }
            )
