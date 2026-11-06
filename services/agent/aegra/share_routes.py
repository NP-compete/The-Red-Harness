"""Share a conversation by link."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.settings import settings
from agent.src.sharing import store
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["sharing"])

_TIMEOUT = settings.SHARE_REQUEST_TIMEOUT_SECONDS


class ShareRequest(BaseModel):
    """Who may open a share link, and for how long."""

    scope: str = Field(default="authenticated")
    expiry_days: int = Field(default=store.DEFAULT_EXPIRY_DAYS, ge=1)


class ShareOut(BaseModel):
    """A published snapshot, as the API returns it."""

    model_config = ConfigDict(extra="allow")

    share_id: str
    thread_id: str
    title: str
    scope: str
    active: bool
    created_at: str
    expires_at: str | None = None
    revoked_at: str | None = None
    views: int = 0
    last_viewed_at: str | None = None
    path: str = ""
    messages: int | None = None
    attachment_names: list[str] | None = None


class ThreadShareOut(BaseModel):
    """Whether this conversation is shared, and how it has been used."""

    model_config = ConfigDict(extra="allow")

    shared: bool
    share_id: str | None = None
    thread_id: str | None = None
    title: str | None = None
    scope: str | None = None
    active: bool | None = None
    created_at: str | None = None
    expires_at: str | None = None
    revoked_at: str | None = None
    views: int | None = None
    last_viewed_at: str | None = None
    path: str | None = None


class UnsharedOut(BaseModel):
    """Whether a link was revoked, or there was none to revoke."""

    revoked: bool


@router.post("/threads/{thread_id}/share", responses={200: {"model": ShareOut}})
async def share_thread(
    thread_id: str, body: ShareRequest, request: Request
) -> dict[str, Any]:
    """Publish a snapshot of this conversation behind a link."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)

    headers = {}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth

    async with httpx.AsyncClient(
        base_url=settings.loopback_base_url,
        headers=headers,
        timeout=_TIMEOUT,
    ) as client:
        state = await client.get(f"/threads/{thread_id}/state")
        if state.status_code != 200:
            raise HTTPException(status_code=404, detail="Thread not found")
        meta = await client.get(f"/threads/{thread_id}")

    values = (state.json() or {}).get("values") or {}
    title = ""
    if meta.status_code == 200:
        title = str(((meta.json() or {}).get("metadata") or {}).get("title") or "")

    snapshot = store.build_snapshot(values, title or "Shared conversation")
    if not snapshot["messages"]:
        raise HTTPException(
            status_code=422, detail="There is nothing in this conversation to share"
        )

    try:
        share = await store.create_share(
            thread_id=thread_id,
            owner_id=user_id,
            title=snapshot["title"],
            snapshot=snapshot,
            scope=body.scope,
            expiry_days=body.expiry_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    result = share.as_dict()
    result["path"] = f"/shared/{share.share_id}"
    result["messages"] = len(snapshot["messages"])
    result["attachment_names"] = snapshot["attachment_names"]
    return result


@router.get("/threads/{thread_id}/share", responses={200: {"model": ThreadShareOut}})
async def get_thread_share(thread_id: str, request: Request) -> dict[str, Any]:
    """Whether this conversation is shared, and how it has been used."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)
    share = await store.get_share_for_thread(thread_id, user_id)
    if share is None:
        return {"shared": False}
    return {
        "shared": share.active,
        **share.as_dict(),
        "path": f"/shared/{share.share_id}",
    }


@router.delete("/threads/{thread_id}/share", responses={200: {"model": UnsharedOut}})
async def unshare_thread(thread_id: str, request: Request) -> dict[str, Any]:
    """Revoke the link."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)
    revoked = await store.revoke_share(thread_id, user_id)
    return {"revoked": revoked}


class MySharesOut(BaseModel):
    """Everything this person has published."""

    shares: list[ShareOut]


class SharedConversationOut(BaseModel):
    """A published snapshot, as a recipient sees it."""

    share_id: str
    title: str = ""
    scope: str = ""
    captured_at: str | None = None
    messages: list[Any] = []
    attachment_names: list[str] = []


@router.get("/shares", responses={200: {"model": MySharesOut}})
async def my_shares(request: Request) -> dict[str, Any]:
    """Everything this user has shared."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)
    shares = await store.list_shares(user_id)
    return {
        "shares": [
            {**share.as_dict(), "path": f"/shared/{share.share_id}"} for share in shares
        ]
    }


@router.get(
    "/shared/{share_id}",
    response_model=None,
    responses={200: {"model": SharedConversationOut}},
)
async def read_shared(share_id: str, request: Request) -> dict[str, Any] | JSONResponse:
    """Read a shared conversation."""
    found = await store.read_share(share_id)
    if found is None:
        raise HTTPException(status_code=404, detail="This link is not valid")

    share, snapshot = found

    if share.scope != "public":
        await authenticated_user_id(request, reject_anonymous=True)

    if not share.active:
        revoked = share.revoked_at is not None
        return JSONResponse(
            status_code=410,
            content={
                "error": "revoked" if revoked else "expired",
                "message": (
                    "This link was revoked" if revoked else "This link has expired"
                ),
                "details": None,
            },
        )

    return {
        "share_id": share.share_id,
        "title": share.title,
        "scope": share.scope,
        "captured_at": snapshot.get("captured_at"),
        "messages": snapshot.get("messages", []),
        "attachment_names": snapshot.get("attachment_names", []),
    }
