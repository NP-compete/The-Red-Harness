"""Withdraw a question, and everything that followed from it."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agent.aegra.auth_helpers import authenticated_user_id
from agent.aegra.fork_routes import _client
from agent.src.agent.thread_history import shown_messages
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["threads"])


class TruncateRequest(BaseModel):
    """Request body withdrawing a thread's messages from a point."""

    message_index: int = Field(
        description="The first message to drop. Everything from here is withdrawn.",
    )


def _removals(
    messages: list[dict[str, Any]], message_index: int
) -> list[dict[str, str]]:
    """Removal markers for every message from the index onward."""
    if message_index < 0:
        raise HTTPException(status_code=400, detail="message_index cannot be negative")

    dropped = messages[message_index:]
    for message in dropped:
        if not message.get("id"):
            raise HTTPException(
                status_code=409,
                detail="This conversation has a turn that cannot be withdrawn.",
            )
    return [{"type": "remove", "id": str(m["id"]), "content": ""} for m in dropped]


class TruncatedOut(BaseModel):
    """The thread truncated, and how many messages went."""

    thread_id: str
    removed: int


@router.post("/threads/{thread_id}/truncate", responses={200: {"model": TruncatedOut}})
async def truncate_thread(
    thread_id: str, body: TruncateRequest, request: Request
) -> dict[str, Any]:
    """Drop the turns from `message_index` onward."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    async with _client(request) as client:
        history_response = await client.get(f"/threads/{thread_id}/history")
        if history_response.status_code == 404:
            raise HTTPException(status_code=404, detail="Thread not found")
        if history_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Could not read thread history")

        history = history_response.json() or []
        if not isinstance(history, list) or not history:
            raise HTTPException(status_code=400, detail="Thread has no history")

        removals = _removals(shown_messages(history), body.message_index)
        if not removals:
            return {"thread_id": thread_id, "removed": 0}

        applied = await client.post(
            f"/threads/{thread_id}/state",
            json={"values": {"messages": removals}},
        )
        if applied.status_code not in (200, 201):
            logger.error(
                "Truncating %s failed (%s): %s",
                thread_id,
                applied.status_code,
                applied.text[:200],
            )
            raise HTTPException(
                status_code=502, detail="Could not withdraw those turns"
            )

    logger.info("Withdrew %d turn(s) from %s for %s", len(removals), thread_id, user_id)
    return {"thread_id": thread_id, "removed": len(removals)}
