"""Naming the documents an answer actually came from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.src.knowledge.citations import Chunk, attribute


@dataclass(frozen=True)
class Citation:
    """One cited document, and the scope it was read from."""

    document_id: str
    title: str
    scope: str

    def as_dict(self) -> dict[str, Any]:
        """Plain data: this travels in the turn's notes."""
        return {
            "document_id": self.document_id,
            "title": self.title,
            "scope": self.scope,
        }


def cite(*, answer: str, found: Any) -> list[Citation]:
    """The documents this answer borrowed from, each named once."""
    documents = getattr(found, "documents", None) or []
    if not answer.strip() or not documents:
        return []

    by_id = {document.id: document for document in documents}
    attributed = attribute(
        answer=answer,
        chunks=[
            Chunk(
                chunk_id=document.id,
                document=document.id,
                text=document.text,
                score=1.0,
            )
            for document in documents
        ],
    )

    cited: list[Citation] = []
    seen: set[str] = set()
    for chunk in attributed.used:
        if chunk.document in seen:
            continue
        seen.add(chunk.document)

        document = by_id.get(chunk.document)
        if document is None:
            continue
        cited.append(
            Citation(
                document_id=document.id,
                title=document.title or document.id.rsplit("/", 1)[-1],
                scope=document.scope.value,
            )
        )
    return cited
