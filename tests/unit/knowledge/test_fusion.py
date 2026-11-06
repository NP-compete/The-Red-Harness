"""Merging keyword and vector results into one ranking."""

from __future__ import annotations

from agent.src.knowledge.fusion import Hit, fuse


def hits(*ids: str) -> list[Hit]:
    return [Hit(chunk_id=i, score=1.0) for i in ids]


def test_nothing_in_means_nothing_out():
    assert fuse(keyword=[], vector=[]) == []


def test_one_engine_alone_keeps_its_order():
    assert [h.chunk_id for h in fuse(keyword=hits("a", "b", "c"), vector=[])] == [
        "a",
        "b",
        "c",
    ]


def test_a_chunk_found_by_both_engines_outranks_one_found_by_either():
    merged = fuse(keyword=hits("x", "only_keyword"), vector=hits("only_vector", "x"))
    assert merged[0].chunk_id == "x"


def test_a_chunk_is_never_returned_twice():
    merged = fuse(keyword=hits("a", "b"), vector=hits("b", "a"))
    assert sorted(h.chunk_id for h in merged) == ["a", "b"]


def test_rank_matters_more_than_raw_score():
    keyword = [Hit(chunk_id="first", score=0.01), Hit(chunk_id="second", score=0.99)]
    assert [h.chunk_id for h in fuse(keyword=keyword, vector=[])][0] == "first"


def test_an_exact_term_match_survives_a_weak_vector_ranking():
    merged = fuse(
        keyword=hits("error-code-512"),
        vector=hits("v1", "v2", "v3", "v4", "error-code-512"),
    )
    assert merged[0].chunk_id == "error-code-512"


def test_weighting_can_favour_one_engine():
    merged = fuse(
        keyword=hits("k"), vector=hits("v"), keyword_weight=2.0, vector_weight=1.0
    )
    assert merged[0].chunk_id == "k"


def test_the_result_can_be_capped():
    assert len(fuse(keyword=hits("a", "b", "c", "d"), vector=[], top_k=2)) == 2


def test_each_result_says_which_engines_found_it():
    merged = fuse(keyword=hits("a"), vector=hits("a", "b"))
    found = {h.chunk_id: h.found_by for h in merged}
    assert found["a"] == ("keyword", "vector")
    assert found["b"] == ("vector",)


def test_fused_scores_decrease_down_the_list():
    merged = fuse(keyword=hits("a", "b", "c"), vector=hits("c", "b", "a"))
    scores = [h.score for h in merged]
    assert scores == sorted(scores, reverse=True)
