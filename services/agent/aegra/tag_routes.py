"""Tags on conversations."""

from __future__ import annotations

import re
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request
from psycopg.rows import DictRow, dict_row
from pydantic import BaseModel, Field

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["threads"])

MAX_TAG_LENGTH = settings.MAX_TAG_LENGTH

MAX_TAGS_PER_THREAD = settings.MAX_TAGS_PER_THREAD

_ALLOWED = re.compile(r"^[a-z0-9][a-z0-9 _-]*$")


class TagsRequest(BaseModel):
    """The full tag set for a thread — a replace, not an append."""

    tags: list[str] = Field(default_factory=list)


def normalise_tag(raw: str) -> str:
    """Fold a tag to its canonical form, or raise."""
    tag = " ".join(str(raw or "").strip().lower().split())
    if not tag:
        raise ValueError("a tag cannot be empty")
    if len(tag) > MAX_TAG_LENGTH:
        raise ValueError(f"'{tag[:20]}…' is longer than {MAX_TAG_LENGTH} characters")
    if not _ALLOWED.match(tag):
        raise ValueError(
            f"'{tag}' may only contain letters, digits, spaces, hyphens and underscores"
        )
    return tag


def normalise_tags(raw: list[str]) -> list[str]:
    """Normalise, de-duplicate and order a tag list."""
    seen: set[str] = set()
    for item in raw:
        seen.add(normalise_tag(item))
        if len(seen) > MAX_TAGS_PER_THREAD:
            raise ValueError(
                f"a conversation may have at most {MAX_TAGS_PER_THREAD} tags"
            )
    return sorted(seen)


async def _connect() -> psycopg.AsyncConnection[DictRow]:
    return await psycopg.AsyncConnection.connect(
        settings.database_uri, row_factory=dict_row
    )


class ThreadTagsOut(BaseModel):
    """The tags on one conversation."""

    thread_id: str
    tags: list[str] = []


@router.put("/threads/{thread_id}/tags", responses={200: {"model": ThreadTagsOut}})
async def set_tags(
    thread_id: str, body: TagsRequest, request: Request
) -> dict[str, Any]:
    """Replace a conversation's tags."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    try:
        tags = normalise_tags(body.tags)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    async with await _connect() as conn:
        result = await conn.execute(
            """
            UPDATE thread
               SET metadata_json = jsonb_set(
                       metadata_json, '{tags}', %(tags)s::jsonb, true
                   ),
                   updated_at = now()
             WHERE thread_id = %(thread_id)s AND user_id = %(user_id)s
            RETURNING thread_id
            """,
            {
                "tags": psycopg.types.json.Json(tags),
                "thread_id": thread_id,
                "user_id": user_id,
            },
        )
        if await result.fetchone() is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        await conn.commit()

    return {"thread_id": thread_id, "tags": tags}


@router.get("/threads/{thread_id}/tags", responses={200: {"model": ThreadTagsOut}})
async def get_tags(thread_id: str, request: Request) -> dict[str, Any]:
    """A conversation's tags."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    async with await _connect() as conn:
        row = await (
            await conn.execute(
                """
                SELECT metadata_json -> 'tags' AS tags
                  FROM thread
                 WHERE thread_id = %(thread_id)s AND user_id = %(user_id)s
                """,
                {"thread_id": thread_id, "user_id": user_id},
            )
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"thread_id": thread_id, "tags": row.get("tags") or []}


class TagCountOut(BaseModel):
    """One tag and how many conversations carry it."""

    model_config = {"extra": "allow"}

    tag: str = ""
    count: int = 0


class TagListOut(BaseModel):
    """Every tag in use, with its count."""

    tags: list[TagCountOut]


class TaggedThreadOut(BaseModel):
    """One conversation found by tag."""

    thread_id: str
    title: str | None = None
    tags: list[str] = []
    updated_at: str | None = None


class TaggedThreadsOut(BaseModel):
    """Every conversation carrying a tag."""

    tag: str
    threads: list[TaggedThreadOut]


@router.get("/tags", responses={200: {"model": TagListOut}})
async def list_tags(request: Request) -> dict[str, Any]:
    """Every tag this user has used, with counts."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    async with await _connect() as conn:
        rows = await (
            await conn.execute(
                """
                SELECT tag, COUNT(*) AS threads
                  FROM thread,
                       LATERAL jsonb_array_elements_text(
                           CASE WHEN jsonb_typeof(metadata_json -> 'tags') = 'array'
                                THEN metadata_json -> 'tags' ELSE '[]'::jsonb END
                       ) AS tag
                 WHERE user_id = %(user_id)s
                 GROUP BY tag
                 ORDER BY threads DESC, tag
                """,
                {"user_id": user_id},
            )
        ).fetchall()

    return {"tags": [{"tag": r["tag"], "threads": int(r["threads"])} for r in rows]}


@router.get("/tags/{tag}/threads", responses={200: {"model": TaggedThreadsOut}})
async def threads_by_tag(
    tag: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Conversations carrying a tag, newest first."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    try:
        wanted = normalise_tag(tag)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    async with await _connect() as conn:
        rows = await (
            await conn.execute(
                """
                SELECT thread_id,
                       metadata_json ->> 'title' AS title,
                       metadata_json -> 'tags'   AS tags,
                       updated_at
                  FROM thread
                 WHERE user_id = %(user_id)s
                   AND metadata_json @> %(probe)s::jsonb
                 ORDER BY updated_at DESC
                 LIMIT %(limit)s
                """,
                {
                    "user_id": user_id,
                    "probe": psycopg.types.json.Json({"tags": [wanted]}),
                    "limit": limit,
                },
            )
        ).fetchall()

    return {
        "tag": wanted,
        "threads": [
            {
                "thread_id": r["thread_id"],
                "title": r["title"],
                "tags": r["tags"] or [],
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in rows
        ],
    }
