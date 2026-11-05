"""Search a user's own conversations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.search.index import refresh_user, search
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/search", tags=["search"])


class SearchResultOut(BaseModel):
    """One conversation matching a search."""

    model_config = {"extra": "allow"}

    thread_id: str = ""
    title: str = ""


class SearchOut(BaseModel):
    """Conversations matching a search, newest first."""

    query: str
    count: int
    results: list[SearchResultOut]


class ReindexedOut(BaseModel):
    """How many threads were put back into the search index."""

    indexed: int


@router.get("/threads", responses={200: {"model": SearchOut}})
async def search_threads(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    refresh: bool = Query(
        True,
        description="Reindex this user's changed threads first. Disable for paging.",
    ),
) -> dict[str, Any]:
    """Full-text search across the caller's threads."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    if refresh:
        try:
            await refresh_user(user_id)
        except Exception:
            logger.exception("Search index refresh failed for %s", user_id)

    try:
        results = await search(user_id, q, limit=limit, offset=offset)
    except Exception:
        logger.exception("Search failed for %s", user_id)
        raise HTTPException(status_code=500, detail="Search failed") from None

    return {"query": q, "count": len(results), "results": results}


@router.post("/reindex", responses={200: {"model": ReindexedOut}})
async def reindex(request: Request) -> dict[str, Any]:
    """Force a reindex of the caller's threads."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)
    return {"indexed": await refresh_user(user_id)}
