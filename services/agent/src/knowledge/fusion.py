"""Combines keyword and vector results into a single ranking."""

from __future__ import annotations

from dataclasses import dataclass, replace

_RANK_CONSTANT = 60


@dataclass(frozen=True)
class Hit:
    """One retrieved chunk, its score, and which engines found it."""

    chunk_id: str
    score: float
    found_by: tuple[str, ...] = ()


def fuse(
    *,
    keyword: list[Hit],
    vector: list[Hit],
    keyword_weight: float = 1.0,
    vector_weight: float = 1.0,
    top_k: int | None = None,
) -> list[Hit]:
    """Combine keyword and vector hits into one weighted ranking."""
    scores: dict[str, float] = {}
    engines: dict[str, list[str]] = {}

    for name, results, weight in (
        ("keyword", keyword, keyword_weight),
        ("vector", vector, vector_weight),
    ):
        for rank, hit in enumerate(results, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + weight / (
                _RANK_CONSTANT + rank
            )
            engines.setdefault(hit.chunk_id, []).append(name)

    ordered = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
    fused = [
        Hit(
            chunk_id=chunk_id, score=scores[chunk_id], found_by=tuple(engines[chunk_id])
        )
        for chunk_id in ordered
    ]
    return fused[:top_k] if top_k is not None else fused


def with_scores(hits: list[Hit], scores: dict[str, float]) -> list[Hit]:
    """Re-rank an existing list, keeping anything the reranker did not score."""
    rescored = [replace(h, score=scores.get(h.chunk_id, h.score)) for h in hits]
    return sorted(rescored, key=lambda h: h.score, reverse=True)
