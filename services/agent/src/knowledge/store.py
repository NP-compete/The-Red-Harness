"""Documents that outlive a conversation, reachable through a scope."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.src.knowledge.scopes import Scope, Viewer


class ScopeViolation(PermissionError):
    """Something was asked for from outside the scope it lives in."""


KEPT = (Scope.SESSION, Scope.USER, Scope.TEAM, Scope.AGENT)
KEPT_SCOPES_SAID = "this store keeps session, user, team and agent documents"

_EDGE = ".,;:!?()[]{}<>\"'`"


def terms_in(text: str) -> set[str]:
    """The searchable terms in a piece of text, lowercased."""
    return {
        stripped for word in text.lower().split() if (stripped := word.strip(_EDGE))
    }


def _check_kept(scope: Scope) -> None:
    """Raise if `scope` is not one of the scopes actually kept."""
    if scope not in KEPT:
        raise NotImplementedError(
            f"{KEPT_SCOPES_SAID}; {scope.value} is not one of them"
        )


@dataclass(frozen=True)
class Document:
    """One stored document and the scope it sits in."""

    id: str
    text: str
    scope: Scope
    owner: str | None = None
    thread_id: str | None = None
    team: str | None = None
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Hit:
    """A document and how well it matched the question."""

    document: Document
    score: float


def _check_coherent(document: Document) -> None:
    """Refuse a document whose scope and keys disagree."""
    if document.scope is Scope.USER and not document.owner:
        raise ValueError("a user-scope document needs an owner")
    if document.scope is Scope.SESSION and not document.thread_id:
        raise ValueError("a session-scope document needs a conversation")
    if document.scope is Scope.AGENT and (document.owner or document.thread_id):
        raise ValueError(
            "an agent-scope document belongs to everyone using the agent; "
            "an owner on it reads as a restriction nothing enforces"
        )
    if document.scope is Scope.TEAM:
        if not document.team:
            raise ValueError("a team-scope document needs a team")
        if document.owner:
            raise ValueError(
                "a team-scope document belongs to the team, not to a person"
            )


def _reachable(document: Document, *, scope: Scope, viewer: Viewer) -> bool:
    """The whole access rule, in one place."""
    if document.scope is not scope:
        return False

    if scope is Scope.AGENT:
        return True
    if scope is Scope.USER:
        return bool(document.owner) and document.owner == viewer.subject
    if scope is Scope.TEAM:
        return bool(document.team) and document.team in viewer.teams
    return bool(viewer.thread_id) and document.thread_id == viewer.thread_id


@dataclass
class InMemoryStore:
    """The reference implementation of the two rules."""

    _documents: dict[str, Document] = field(default_factory=dict)

    def add(self, document: Document) -> None:
        """Store `document`, rejecting an incoherent scope."""
        _check_coherent(document)
        self._documents[document.id] = document

    def search(
        self,
        query: str,
        *,
        scope: Scope,
        viewer: Viewer,
        top_k: int = 8,
    ) -> list[Document]:
        """Documents matching `query`, inside `scope`, visible to `viewer`."""
        return [
            hit.document
            for hit in self.search_scored(
                query, scope=scope, viewer=viewer, top_k=top_k
            )
        ]

    def search_scored(
        self,
        query: str,
        *,
        scope: Scope,
        viewer: Viewer,
        top_k: int = 8,
    ) -> list[Hit]:
        """The same search, saying how well each document matched."""
        _check_kept(scope)
        words = terms_in(query)
        if not words:
            return []

        found = [
            Hit(document=document, score=len(shared) / len(words))
            for document in self._documents.values()
            if _reachable(document, scope=scope, viewer=viewer)
            and (shared := words & terms_in(document.text))
        ]
        found.sort(key=lambda hit: hit.score, reverse=True)
        return found[:top_k]

    def get(self, document_id: str, *, viewer: Viewer) -> Document | None:
        """One document, if this viewer may reach it."""
        document = self._documents.get(document_id)
        if document is None:
            return None

        if not _reachable(document, scope=document.scope, viewer=viewer):
            raise ScopeViolation(f"{document_id} is not reachable from here")
        return document

    def remove(self, document_id: str, *, viewer: Viewer) -> None:
        """Remove `document_id` if `viewer` can see it."""
        if self.get(document_id, viewer=viewer) is None:
            return
        del self._documents[document_id]

    def documents_in(self, *, scope: Scope, owner: str | None = None) -> list[Document]:
        """Everything in one scope, optionally one owner's."""
        return [
            document
            for document in self._documents.values()
            if document.scope is scope and (owner is None or document.owner == owner)
        ]

    def forget_corpus(self, *, prefix: str, keeping: set[str]) -> int:
        """Drop agent documents under `prefix` that are not in `keeping`."""
        from_a_corpus = (Scope.AGENT, Scope.TEAM)
        departed = [
            document_id
            for document_id, document in self._documents.items()
            if document.scope in from_a_corpus
            and document_id.startswith(prefix)
            and document_id not in keeping
        ]
        for document_id in departed:
            del self._documents[document_id]
        return len(departed)

    def forget_thread(self, thread_id: str) -> None:
        """Drop a conversation's documents when the conversation goes."""
        for document_id in [
            found.id
            for found in self._documents.values()
            if found.scope is Scope.SESSION and found.thread_id == thread_id
        ]:
            del self._documents[document_id]


_SESSION_STORE: InMemoryStore | None = None


def session_store() -> InMemoryStore:
    """The store this process keeps documents in."""
    global _SESSION_STORE
    if _SESSION_STORE is None:
        _SESSION_STORE = InMemoryStore()
    return _SESSION_STORE
