"""Fork a conversation at an earlier turn."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.agent.thread_history import shown_messages
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["threads"])

_TIMEOUT = settings.FORK_REQUEST_TIMEOUT_SECONDS


class ForkRequest(BaseModel):
    """Where to cut."""

    checkpoint_id: str | None = None
    message_index: int | None = Field(default=None, ge=0)
    title: str | None = Field(default=None, max_length=200)


def _client(request: Request) -> httpx.AsyncClient:
    """Loopback client carrying the caller's own credentials."""
    headers = {}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth
    return httpx.AsyncClient(
        base_url=settings.loopback_base_url,
        headers=headers,
        timeout=_TIMEOUT,
    )


def _messages_at(history: list[dict[str, Any]], checkpoint_id: str) -> list[dict]:
    for entry in history:
        if entry.get("checkpoint_id") == checkpoint_id:
            return list((entry.get("values") or {}).get("messages") or [])
    raise HTTPException(status_code=404, detail="Checkpoint not found in this thread")


def messages_for_fork(history: list[dict[str, Any]], message_index: int) -> list[dict]:
    """Everything up to the message at `message_index` in the shown list."""
    if message_index <= 0:
        return []

    shown = shown_messages(history)
    cut = shown[:message_index]
    if not cut:
        return []

    anchor = cut[-1].get("id") if isinstance(cut[-1], dict) else None
    if not anchor:
        return cut

    best = cut
    for entry in history:
        messages = (entry.get("values") or {}).get("messages") or []
        for position, message in enumerate(messages):
            if isinstance(message, dict) and message.get("id") == anchor:
                if position + 1 > len(best):
                    best = list(messages[: position + 1])
                break
    return best


def _strip_for_replay(messages: list[Any]) -> list[dict]:
    """Drop fields that must not be copied into a new thread."""
    cleaned = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        copy = {k: v for k, v in message.items() if k not in ("id", "run_id")}
        if copy.get("type") in ("human", "ai", "system", "tool"):
            copy["id"] = str(uuid.uuid4())
            cleaned.append(copy)
    return cleaned


class ForkedOut(BaseModel):
    """The new conversation a fork produced, and where it was cut."""

    thread_id: str
    forked_from: str
    message_count: int


@router.post("/threads/{thread_id}/fork", responses={200: {"model": ForkedOut}})
async def fork_thread(
    thread_id: str, body: ForkRequest, request: Request
) -> dict[str, Any]:
    """Copy a conversation up to a point into a new thread."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    if body.checkpoint_id is None and body.message_index is None:
        raise HTTPException(
            status_code=400, detail="Provide checkpoint_id or message_index"
        )

    async with _client(request) as client:
        history_response = await client.get(f"/threads/{thread_id}/history")
        if history_response.status_code == 404:
            raise HTTPException(status_code=404, detail="Thread not found")
        if history_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Could not read thread history")

        history = history_response.json() or []
        if not isinstance(history, list) or not history:
            raise HTTPException(status_code=400, detail="Thread has no history to fork")

        if body.checkpoint_id:
            messages = _messages_at(history, body.checkpoint_id)
        else:
            messages = messages_for_fork(history, body.message_index or 0)

        messages = _strip_for_replay(messages)
        if not messages:
            raise HTTPException(status_code=400, detail="Nothing to fork at that point")

        source = await client.get(f"/threads/{thread_id}")
        source_metadata = (
            (source.json() or {}).get("metadata") or {}
            if source.status_code == 200
            else {}
        )

        created = await client.post(
            "/threads",
            json={
                "metadata": _fork_metadata(
                    source_metadata,
                    title=body.title or _forked_title(source_metadata),
                    thread_id=thread_id,
                    checkpoint=body.checkpoint_id,
                    message_count=len(messages),
                ),
            },
        )
        if created.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail="Could not create the fork")
        new_thread_id = created.json()["thread_id"]

        seeded = await client.post(
            f"/threads/{new_thread_id}/state",
            json={
                "values": {"messages": messages},
                "assistant_id": source_metadata.get("assistant_id") or "agent",
            },
        )
        if seeded.status_code not in (200, 201):
            await client.delete(f"/threads/{new_thread_id}")
            logger.error(
                "Fork seeding failed (%s): %s", seeded.status_code, seeded.text[:200]
            )
            raise HTTPException(status_code=502, detail="Could not seed the fork")

    logger.info(
        "Forked thread %s -> %s (%d messages) for %s",
        thread_id,
        new_thread_id,
        len(messages),
        user_id,
    )
    return {
        "thread_id": new_thread_id,
        "forked_from": thread_id,
        "message_count": len(messages),
    }


def _fork_metadata(
    source: dict[str, Any],
    *,
    title: str,
    thread_id: str,
    checkpoint: Any,
    message_count: int,
) -> dict[str, Any]:
    """What the copy records about itself."""
    metadata: dict[str, Any] = {
        "graph_id": source.get("graph_id") or "agent",
        "assistant_id": source.get("assistant_id") or "agent",
        "thread_name": title,
        "forked_from": thread_id,
        "forked_at_checkpoint": checkpoint,
        "forked_message_count": message_count,
        "project_id": source.get("project_id"),
    }
    for key in ("user_identity", "owner"):
        if source.get(key) is not None:
            metadata[key] = source[key]
    return metadata


def _forked_title(metadata: dict[str, Any]) -> str:
    """What to call the copy."""
    from agent.src.agent.thread_title import PLACEHOLDER, suggest_title

    original = str(metadata.get("thread_name") or "").strip()
    if not original:
        return "Forked conversation"

    named = suggest_title(original, max_length=40)
    if named.text == PLACEHOLDER:
        return "Forked conversation"
    return f"{named.text} (fork)"
