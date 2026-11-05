"""Asking the library a question, on behalf of a turn."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, Hit

_WIDE = 50


class RetrievalRefused(ValueError):
    """The question cannot be asked as put."""


@dataclass(frozen=True)
class Found:
    """What retrieval turned up, and what fell below the threshold."""

    documents: list[Document] = field(default_factory=list)
    scope: Scope | None = None
    searched: tuple[Scope, ...] = ()
    hits: tuple[Hit, ...] = ()
    below_threshold: tuple[Hit, ...] = ()


def retrieve(
    question: str,
    *,
    store: Any,
    viewer: Viewer,
    config: Knowledge,
    scope: Scope | None = None,
) -> Found:
    """Documents for this question, from exactly one scope."""
    if not config.enabled:
        raise RetrievalRefused("the document library is not enabled here")

    if not question.strip():
        raise RetrievalRefused("a retrieval needs something to look for")

    if scope is not None:
        if scope not in config.scopes:
            raise RetrievalRefused(
                f"{scope.value} documents are not kept by this deployment"
            )
        return _one(question, scope=scope, store=store, viewer=viewer, config=config)

    last = Found(documents=[], scope=None, searched=config.order)
    for candidate in config.order:
        found = _one(
            question, scope=candidate, store=store, viewer=viewer, config=config
        )
        if found.documents:
            return Found(
                documents=found.documents,
                scope=candidate,
                searched=config.order,
                hits=found.hits,
                below_threshold=found.below_threshold,
            )
        if found.below_threshold:
            last = Found(
                documents=[],
                scope=None,
                searched=config.order,
                below_threshold=found.below_threshold,
            )

    return last


def _one(
    question: str,
    *,
    scope: Scope,
    store: Any,
    viewer: Viewer,
    config: Knowledge,
) -> Found:
    """Retrieve from one scope, keeping what clears the threshold."""
    scored = store.search_scored(question, scope=scope, viewer=viewer, top_k=_WIDE)

    kept = [hit for hit in scored if hit.score >= config.min_score]
    missed = [hit for hit in scored if hit.score < config.min_score]

    kept = kept[: config.top_k]
    return Found(
        documents=[hit.document for hit in kept],
        scope=scope if kept else None,
        searched=(scope,),
        hits=tuple(kept),
        below_threshold=tuple(missed),
    )
