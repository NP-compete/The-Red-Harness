"""Asking for a conversation to be handed to somebody else."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.src.security.handing_over import hand_over
from agent.src.security.ownership_transfer import Thread, Transfer
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["handover"])


class HandoverRequest(BaseModel):
    """Request body handing a conversation to someone else."""

    to: str
    accepted: bool = False


async def _who(request: Request) -> str:
    """The authenticated caller."""
    from agent.aegra.auth_helpers import authenticated_user_id

    return await authenticated_user_id(request, reject_anonymous=True)


def _thread_facts(thread_id: str, owner: str) -> Thread:
    """What is known about the conversation being handed over."""
    return Thread(
        thread=thread_id,
        owner=owner,
        org="",
        readers=(owner,),
        guests=(),
        under_legal_hold=False,
        contains_personal_data=False,
    )


def _servers_used(thread_id: str) -> list[str]:
    """Which integrations this conversation has reached for."""
    from agent.src.agent.config import agent_config

    try:
        return sorted(agent_config.get_mcp_servers())
    except Exception:
        return []


def _connections_of(subject: str) -> list[str]:
    """Which of them the receiver has already connected."""
    return []


class HandoverOut(BaseModel):
    """Whether the handover went through, and what it needs."""

    allowed: bool
    waiting: bool
    reason: str = ""
    needs_connecting: list[str] = []
    already_connected: list[str] = []
    warning: str = ""
    guests_dropped: list[str] = []


@router.post("/threads/{thread_id}/handover", responses={200: {"model": HandoverOut}})
async def hand_thread_over(
    thread_id: str, body: HandoverRequest, request: Request
) -> dict[str, Any]:
    """Hand a conversation over to someone else."""
    asked_by = await _who(request)
    thread = _thread_facts(thread_id, asked_by)

    if body.to == thread.owner:
        raise HTTPException(
            status_code=400, detail="This conversation is already theirs"
        )

    found = hand_over(
        thread,
        transfer=Transfer(
            to=body.to,
            to_org=thread.org,
            asked_by=asked_by,
            accepted=body.accepted,
        ),
        servers_used=_servers_used(thread_id),
        receiver_connections=_connections_of(body.to),
    )

    if not found.allowed and not found.waiting:
        raise HTTPException(status_code=403, detail=found.reason)

    return {
        "allowed": found.allowed,
        "waiting": found.waiting,
        "reason": found.reason,
        "needs_connecting": list(found.needs_connecting),
        "already_connected": list(found.already_connected),
        "warning": found.warning,
        "guests_dropped": found.guests_dropped,
    }
