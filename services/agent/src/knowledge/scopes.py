"""Who may search which collection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Scope(str, Enum):
    """How widely a collection is shared."""

    SESSION = "session"
    USER = "user"
    TEAM = "team"
    AGENT = "agent"


@dataclass(frozen=True)
class Viewer:
    """Who is looking, and the teams and thread they bring."""

    subject: str
    teams: tuple[str, ...]
    thread_id: str | None


@dataclass(frozen=True)
class Collection:
    """One knowledge collection and the scope it sits in."""

    name: str
    scope: Scope
    owner: str | None = None
    team: str | None = None
    thread_id: str | None = None


def can_read(collection: Collection, viewer: Viewer) -> bool:
    """Whether `viewer` may read `collection`."""
    if collection.scope is Scope.AGENT:
        return True
    if collection.scope is Scope.USER:
        return collection.owner is not None and collection.owner == viewer.subject
    if collection.scope is Scope.TEAM:
        return collection.team is not None and collection.team in viewer.teams
    return collection.thread_id is not None and collection.thread_id == viewer.thread_id


def retrieval_filter(viewer: Viewer) -> dict:
    """Criteria for the search itself, so nothing is filtered after the fact."""
    scopes = [Scope.AGENT, Scope.USER]
    if viewer.teams:
        scopes.append(Scope.TEAM)
    if viewer.thread_id is not None:
        scopes.append(Scope.SESSION)

    return {
        "scopes": scopes,
        "owner": viewer.subject,
        "teams": viewer.teams,
        "thread_id": viewer.thread_id,
    }
