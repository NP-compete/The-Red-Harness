"""A person's own documents: add, see, remove."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.src.knowledge.quota import QuotaExceeded, check_room_for, stored_bytes
from agent.src.knowledge.scopes import Scope
from agent.src.knowledge.store import Document, ScopeViolation
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class NewDocument(BaseModel):
    """Request body adding a document to the knowledge store."""

    title: str = ""
    text: str


class KnowledgeDocumentOut(BaseModel):
    """One stored document, without its text."""

    id: str
    title: str
    bytes: int


class TeamDocumentOut(KnowledgeDocumentOut):
    """One stored document shared with a team."""

    team: str


class KnowledgeListOut(BaseModel):
    """The documents a caller can see, and how much of the quota they use."""

    team: list[TeamDocumentOut]
    documents: list[KnowledgeDocumentOut]
    used_bytes: int
    limit_bytes: int


class KnowledgeAddedOut(BaseModel):
    """The id of a newly added document."""

    id: str


class KnowledgeDocumentTextOut(BaseModel):
    """One stored document with its text."""

    id: str
    title: str
    text: str
    editable: bool


class KnowledgeSavedOut(BaseModel):
    """Confirmation that a document was saved."""

    id: str
    status: str


class KnowledgeRemovedOut(BaseModel):
    """Confirmation that a document was removed."""

    status: str


class RewrittenOut(BaseModel):
    """A suggested replacement, or a refusal with a reason."""

    ok: bool
    text: str = ""
    reason: str = ""


def _store() -> Any:
    """The knowledge store bound to this session."""
    from agent.src.knowledge.store import session_store

    return session_store()


async def _owner(request: Request) -> str:
    """Whose documents these are."""
    from agent.aegra.auth_helpers import memory_user_id

    return await memory_user_id(request)


async def _teams_of(request: Request) -> tuple[str, ...]:
    """The groups this caller is in, from the directory."""
    from agent.aegra.auth_helpers import memory_user_id
    from agent.src.knowledge.membership import teams_of

    return await teams_of(await memory_user_id(request))


def _offered() -> Any:
    """The configuration, or a 404 if this is not on offer."""
    from agent.src.agent.config import agent_config

    found = agent_config.get_knowledge_config()
    if not found.enabled or Scope.USER not in found.scopes:
        raise HTTPException(status_code=404, detail="Not Found")
    return found


@router.get("/documents", responses={200: {"model": KnowledgeListOut}})
async def list_documents(request: Request) -> dict[str, Any]:
    """What this person is keeping, and how much room is left."""
    config = _offered()
    owner = await _owner(request)
    store = _store()

    documents = store.documents_in(scope=Scope.USER, owner=owner)

    teams = await _teams_of(request)
    shared = [
        document
        for document in store.documents_in(scope=Scope.TEAM)
        if document.team in teams
    ]

    return {
        "team": [
            {
                "id": document.id,
                "title": document.title,
                "bytes": len(document.text.encode("utf-8")),
                "team": document.team,
            }
            for document in shared
        ],
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "bytes": len(document.text.encode("utf-8")),
            }
            for document in documents
        ],
        "used_bytes": stored_bytes(store, owner=owner),
        "limit_bytes": config.user_max_bytes,
    }


@router.post("/documents", responses={200: {"model": KnowledgeAddedOut}})
async def add_document(request: Request, body: NewDocument) -> dict[str, Any]:
    """Store a new document for the caller, if it fits the quota."""
    config = _offered()
    owner = await _owner(request)
    store = _store()

    text = body.text.strip()
    size = len(text.encode("utf-8"))

    try:
        check_room_for(size, store=store, owner=owner, limit=config.user_max_bytes)
    except ValueError as refused:
        if isinstance(refused, QuotaExceeded):
            raise HTTPException(status_code=413, detail=str(refused)) from None
        raise HTTPException(status_code=400, detail=str(refused)) from None

    document_id = f"user:{uuid.uuid4()}"
    store.add(
        Document(
            id=document_id,
            text=text,
            scope=Scope.USER,
            owner=owner,
            title=body.title.strip() or "Untitled",
        )
    )
    return {"id": document_id}


def read_one(*, store: Any, viewer: Any, document_id: str) -> dict[str, Any]:
    """One document, with its text, for somebody about to edit it."""
    try:
        found = store.get(document_id, viewer=viewer)
    except ScopeViolation:
        raise HTTPException(status_code=403, detail="Not yours to read") from None

    if found is None:
        raise HTTPException(status_code=404, detail="No such document")

    return {
        "id": found.id,
        "title": found.title,
        "text": found.text,
        "editable": found.scope is Scope.USER
        and found.owner == getattr(viewer, "subject", None),
    }


@router.get(
    "/documents/{document_id:path}",
    responses={200: {"model": KnowledgeDocumentTextOut}},
)
async def get_document(request: Request, document_id: str) -> dict[str, Any]:
    """Read one of your documents, or one shared with you."""
    _offered()
    owner = await _owner(request)

    from agent.src.knowledge.membership import teams_of
    from agent.src.knowledge.scopes import Viewer

    return read_one(
        store=_store(),
        viewer=Viewer(subject=owner, teams=await teams_of(owner), thread_id=None),
        document_id=document_id,
    )


def rewrite_document(
    *,
    store: Any,
    viewer: Any,
    document_id: str,
    text: str,
    title: str,
    limit: int,
) -> None:
    """Replace a person's own note, keeping its id."""
    body = text.strip()
    if not body:
        raise HTTPException(status_code=400, detail="A note needs something in it")

    try:
        found = store.get(document_id, viewer=viewer)
    except ScopeViolation:
        raise HTTPException(status_code=403, detail="Not yours to change") from None

    if found is None:
        raise HTTPException(status_code=404, detail="No such document")

    if found.scope is not Scope.USER or found.owner != getattr(viewer, "subject", None):
        raise HTTPException(status_code=403, detail="Not yours to change")

    was = len(found.text.encode("utf-8"))
    size = len(body.encode("utf-8"))
    growth = size - was
    try:
        if growth > 0:
            check_room_for(growth, store=store, owner=found.owner, limit=limit)
    except ValueError as refused:
        if isinstance(refused, QuotaExceeded):
            raise HTTPException(status_code=413, detail=str(refused)) from None
        raise HTTPException(status_code=400, detail=str(refused)) from None

    store.add(
        Document(
            id=document_id,
            text=body,
            scope=Scope.USER,
            owner=found.owner,
            title=title.strip() or found.title or "Untitled",
        )
    )


@router.put(
    "/documents/{document_id:path}", responses={200: {"model": KnowledgeSavedOut}}
)
async def change_document(
    request: Request, document_id: str, body: NewDocument
) -> dict[str, Any]:
    """Rewrite one of your own notes."""
    config = _offered()
    owner = await _owner(request)

    from agent.src.knowledge.membership import teams_of
    from agent.src.knowledge.scopes import Viewer

    rewrite_document(
        store=_store(),
        viewer=Viewer(subject=owner, teams=await teams_of(owner), thread_id=None),
        document_id=document_id,
        text=body.text,
        title=body.title,
        limit=config.user_max_bytes,
    )
    return {"id": document_id, "status": "saved"}


@router.delete(
    "/documents/{document_id:path}", responses={200: {"model": KnowledgeRemovedOut}}
)
async def remove_document(request: Request, document_id: str) -> dict[str, Any]:
    """Remove one of the caller's documents."""
    _offered()
    owner = await _owner(request)
    store = _store()

    from agent.src.knowledge.membership import teams_of
    from agent.src.knowledge.scopes import Viewer

    viewer = Viewer(subject=owner, teams=await teams_of(owner), thread_id=None)

    try:
        found = store.get(document_id, viewer=viewer)
    except ScopeViolation:
        raise HTTPException(status_code=403, detail="Not yours to remove") from None

    if found is None:
        raise HTTPException(status_code=404, detail="No such document")

    if found.scope is not Scope.USER:
        raise HTTPException(
            status_code=403,
            detail="That document comes from this agent's configuration",
        )

    store.remove(document_id, viewer=viewer)
    return {"status": "deleted"}


class Selection(BaseModel):
    """Request body asking the model to rewrite a selected passage."""

    selection: str
    instruction: str


def _ask_model(prompt: str) -> str:
    """One turn, no tools, no history."""
    from agent.src.agent.config import agent_config
    from agent.src.cache.model_cache import get_or_create_model
    from agent.src.settings import settings

    orchestrator = agent_config.get_orchestrator_config()
    answer = get_or_create_model(
        model_name=orchestrator.get("model", settings.DEFAULT_MODEL),
        temperature=0.0,
    ).invoke(prompt)
    return getattr(answer, "content", "") or ""


@router.post("/rewrite", responses={200: {"model": RewrittenOut}})
async def rewrite_passage(request: Request, body: Selection) -> dict[str, Any]:
    """Rewrite a passage somebody selected, as they asked."""
    from starlette.concurrency import run_in_threadpool

    from agent.src.knowledge.rewriting import rewrite_selection

    await _owner(request)

    found = await run_in_threadpool(
        rewrite_selection, body.selection, body.instruction, ask=_ask_model
    )
    return {"ok": found.ok, "text": found.text, "reason": found.reason}
