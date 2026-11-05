"""Showing which sources an answer actually rests on."""

from __future__ import annotations

import pytest

from agent.src.knowledge.citations import Chunk, attribute


def chunk(**kwargs) -> Chunk:
    defaults = {
        "chunk_id": "c1",
        "document": "runbook.md",
        "text": "replica lag is handled by failing over the reader",
        "score": 0.9,
    }
    defaults.update(kwargs)
    return Chunk(**defaults)


def test_a_source_quoted_in_the_answer_is_cited():
    cited = attribute(
        answer="We handle replica lag by failing over the reader.",
        chunks=[chunk()],
    )
    assert cited.used[0].document == "runbook.md"


def test_a_source_the_answer_ignores_is_not_cited():
    cited = attribute(
        answer="Nothing relevant was found.",
        chunks=[chunk()],
    )
    assert cited.used == ()


def test_unused_sources_are_reported_separately():
    cited = attribute(answer="Nothing relevant.", chunks=[chunk()])
    assert cited.retrieved_but_unused[0].document == "runbook.md"


def test_a_document_is_cited_once_however_many_chunks_match():
    cited = attribute(
        answer="replica lag is handled by failing over the reader",
        chunks=[chunk(chunk_id="c1"), chunk(chunk_id="c2")],
    )
    assert len(cited.documents) == 1


def test_citations_keep_the_order_the_answer_uses_them():
    chunks = [
        chunk(chunk_id="a", document="second.md", text="restart the reader replica"),
        chunk(
            chunk_id="b", document="first.md", text="check the replication lag first"
        ),
    ]
    cited = attribute(
        answer="check the replication lag first, then restart the reader replica",
        chunks=chunks,
    )
    assert cited.documents == ("first.md", "second.md")


def test_an_answer_resting_on_nothing_is_flagged():
    assert attribute(answer="I think so.", chunks=[chunk()]).grounded is False


def test_an_answer_resting_on_a_source_is_grounded():
    cited = attribute(
        answer="replica lag is handled by failing over the reader", chunks=[chunk()]
    )
    assert cited.grounded is True


def test_an_answer_with_no_sources_at_all_is_not_grounded():
    assert attribute(answer="Anything.", chunks=[]).grounded is False


def test_short_coincidental_overlap_does_not_count_as_a_citation():
    cited = attribute(answer="the", chunks=[chunk()])
    assert cited.used == ()


@pytest.mark.parametrize("answer", ["", "   "])
def test_an_empty_answer_cites_nothing(answer):
    assert attribute(answer=answer, chunks=[chunk()]).used == ()
