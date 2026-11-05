"""Spaces: rooms several people share with the agent (E33-T1)."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent.aegra.auth_helpers import check_ldap_role
from agent.src.spaces import store, timeline
from agent.src.spaces.addressing import addresses_agent
from agent.src.spaces.approval import ApprovalNotYours, check_may_answer
from agent.src.spaces.errors import SpaceNotFound, SpaceRefused
from agent.src.spaces.membership import is_member
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/spaces", tags=["spaces"])


class SpaceCreate(BaseModel):
    """Request body for creating a space."""

    name: str
    group_cn: str


class SpaceOut(BaseModel):
    """A space as returned to the caller."""

    space_id: str
    name: str
    group_cn: str
    created_by: str
    created_at: str | None = None
    always_on: bool = False


class RunClaim(BaseModel):
    """Request body naming the run a caller wants to claim."""

    run_id: str


class AlwaysOn(BaseModel):
    """Request body toggling a space's always-on setting."""

    always_on: bool


class Addressed(BaseModel):
    """Request body carrying the text to test for an address to the agent."""

    text: str


class ActiveRunOut(BaseModel):
    """The run currently holding a space, if any."""

    run_id: str | None = None
    triggered_by: str | None = None
    at: str | None = None


class SpaceListOut(BaseModel):
    """The spaces visible to the caller."""

    spaces: list[SpaceOut]
    membership: str = "directory groups, asked per request"


class MessageOut(BaseModel):
    """One message in a room."""

    seq: int
    id: str
    space_id: str
    author: str
    body: str
    reply_to: str | None = None
    pinned: bool
    pinned_by: str | None = None
    created_at: str | None = None
    reactions: dict[str, Any] = {}


class TimelineOut(BaseModel):
    """A page of a room's messages plus the cursor for the next page."""

    messages: list[MessageOut]
    next_seq: int


class PinsOut(BaseModel):
    """The pinned messages of a room."""

    pins: list[MessageOut]


class ReactionAddedOut(BaseModel):
    """Confirmation that a reaction was added."""

    message_id: str
    emoji: str
    reactor: str


class ReactionRemovedOut(BaseModel):
    """Confirmation that a reaction was removed."""

    message_id: str
    emoji: str
    removed: bool


class RunReleasedOut(BaseModel):
    """Confirmation that a space's run claim was released."""

    released: bool


class ApprovedOut(BaseModel):
    """Confirmation that a run was approved."""

    approved: bool
    run_id: str | None = None


class AlwaysOnOut(BaseModel):
    """A space's always-on setting after an update."""

    space_id: str
    always_on: bool


class PersonOut(BaseModel):
    """One participant in a space and where membership came from."""

    handle: str
    source: str


class PeopleOut(BaseModel):
    """The participants of a space, the agent handle, and the directory used."""

    people: list[PersonOut]
    agent: str
    directory: str


class SpendRowOut(BaseModel):
    """One person's spend in a space for the period."""

    person: str
    amount: str
    runs: int


class SpendOut(BaseModel):
    """A space's spend for a month, broken down per person."""

    space_id: str
    month: str
    currency: str
    rate_card_version: str
    rows: list[SpendRowOut]
    total: str
    billing: str


class AddressedOut(BaseModel):
    """Whether a message addresses the agent, and why."""

    addressed: bool
    reason: str
    handle: str


class EventStreamResponse(StreamingResponse):
    """Declares the media type the room's stream actually sends."""

    media_type = "text/event-stream"


_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

_NOT_FOUND = JSONResponse(
    status_code=404,
    content={
        "error": "not_found",
        "message": "No such space, or you are not a member of it.",
    },
)


async def _whoami(request: Request) -> str:
    """The authenticated caller, checked against the directory."""
    return await check_ldap_role(request)


@router.get("", response_model=SpaceListOut)
async def list_spaces(request: Request) -> dict[str, Any]:
    """The spaces this person is in."""
    who = await _whoami(request)
    found = [s for s in await store.all_spaces() if await is_member(who, s.group_cn)]
    return {"spaces": [s.as_dict() for s in found]}


@router.post("", response_model=None, responses={200: {"model": SpaceOut}})
async def create_space(
    request: Request, body: SpaceCreate
) -> dict[str, Any] | JSONResponse:
    """Open a room against a directory group."""
    who = await _whoami(request)
    try:
        made = await store.create(
            name=body.name, group_cn=body.group_cn, created_by=who
        )
    except SpaceRefused as exc:
        return JSONResponse(
            status_code=400, content={"error": "bad_request", "message": str(exc)}
        )
    return made.as_dict()


@router.get("/{space_id}", response_model=None, responses={200: {"model": SpaceOut}})
async def read_space(request: Request, space_id: str) -> dict[str, Any] | JSONResponse:
    """One space, if this person is in it."""
    who = await _whoami(request)
    found = await store.get(space_id)
    if found is None or not await is_member(who, found.group_cn):
        return _NOT_FOUND
    return found.as_dict()


async def _member_or_404(request: Request, space_id: str) -> Any:
    """The space, if this person is in it. Otherwise nothing."""
    who = await _whoami(request)
    found = await store.get(space_id)
    if found is None or not await is_member(who, found.group_cn):
        return who, None
    return who, found


@router.get(
    "/{space_id}/run", response_model=None, responses={200: {"model": ActiveRunOut}}
)
async def read_active_run(
    request: Request, space_id: str
) -> dict[str, Any] | JSONResponse:
    """Who is mid-run here, so the room can show it (E31-T4)."""
    _, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND
    running = await store.active_run(space_id)
    if running is None:
        return {"run_id": None, "triggered_by": None, "at": None}
    return {
        "run_id": running.run_id,
        "triggered_by": running.triggered_by,
        "at": running.at,
    }


@router.post(
    "/{space_id}/run", response_model=None, responses={200: {"model": ActiveRunOut}}
)
async def claim_run(
    request: Request, space_id: str, body: RunClaim
) -> dict[str, Any] | JSONResponse:
    """Take the room's single run slot."""
    who, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND
    try:
        taken = await store.claim_run(space_id, run_id=body.run_id, by=who)
    except store.SpaceBusy as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "conflict",
                "message": str(exc),
                "held_by": exc.holder,
            },
        )
    return {"run_id": taken.run_id, "triggered_by": taken.triggered_by, "at": taken.at}


@router.delete(
    "/{space_id}/run/{run_id}",
    response_model=None,
    responses={200: {"model": RunReleasedOut}},
)
async def release_run(
    request: Request, space_id: str, run_id: str
) -> dict[str, Any] | JSONResponse:
    """Give the slot back when the run is done."""
    _, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND
    await store.release_run(space_id, run_id=run_id)
    return {"released": True}


@router.post(
    "/{space_id}/approve", response_model=None, responses={200: {"model": ApprovedOut}}
)
async def approve(request: Request, space_id: str) -> dict[str, Any] | JSONResponse:
    """Answer the pending action — only if the run is yours (E33-T4)."""
    who, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND
    running = await store.active_run(space_id)
    try:
        check_may_answer(running, actor=who, space_id=space_id)
    except ApprovalNotYours as exc:
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "message": str(exc),
                "owner": exc.owner,
            },
        )
    return {"approved": True, "run_id": running.run_id if running else None}


@router.patch(
    "/{space_id}", response_model=None, responses={200: {"model": AlwaysOnOut}}
)
async def set_always_on(
    request: Request, space_id: str, body: AlwaysOn
) -> dict[str, Any] | JSONResponse:
    """Turn always-on for this room on or off (E33-T3)."""
    _, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND
    if not await store.set_always_on(space_id, always_on=body.always_on):
        return _NOT_FOUND
    logger.warning(
        "Space %s always_on set to %s by %s",
        space_id,
        body.always_on,
        await _whoami(request),
    )
    return {"space_id": space_id, "always_on": body.always_on}


@router.get(
    "/{space_id}/people", response_model=None, responses={200: {"model": PeopleOut}}
)
async def read_people(request: Request, space_id: str) -> dict[str, Any] | JSONResponse:
    """Who `@` may address in this room (E41-T3)."""
    who, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND

    import asyncio

    from agent.src.agent.config import agent_config
    from agent.src.ldap.config import ldap_settings
    from agent.src.spaces.people import MAX_PEOPLE, members_of_group_sync

    listed = await asyncio.to_thread(members_of_group_sync, found.group_cn)

    page = await timeline.read(space_id, caller=who, after_seq=0, limit=timeline.PAGE)
    spoke = []
    for message in page["messages"]:
        if message["author"] not in spoke:
            spoke.append(message["author"])

    people = [{"handle": h, "source": "directory"} for h in listed]
    known = set(listed)
    for handle in spoke:
        if handle not in known:
            people.append({"handle": handle, "source": "spoke_here"})

    return {
        "people": people[:MAX_PEOPLE],
        "agent": (agent_config.get_orchestrator_config() or {}).get("name") or "agent",
        "directory": "asked" if ldap_settings.LDAP_URL else "not configured",
    }


@router.get(
    "/{space_id}/spend", response_model=None, responses={200: {"model": SpendOut}}
)
async def read_spend(
    request: Request, space_id: str, month: str = ""
) -> dict[str, Any] | JSONResponse:
    """What this room cost this month, and who spent it."""
    _, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND

    from datetime import datetime, timezone
    from decimal import Decimal

    from agent.aegra.rates_routes import rate_card
    from agent.src.security.cost_attribution import space_charges_in
    from agent.src.settings import settings

    asked = month.strip() or datetime.now(timezone.utc).strftime("%Y-%m")
    if not _MONTH.match(asked):
        return JSONResponse(
            status_code=422,
            content={
                "error": "unprocessable",
                "message": f"{asked!r} is not a month. Ask for one as 2026-03.",
            },
        )

    charges = await space_charges_in(space_id, asked)
    rows = sorted(
        (
            {"person": who, "amount": str(e["amount"]), "runs": e["runs"]}
            for who, e in charges.items()
        ),
        key=lambda row: Decimal(row["amount"]),
        reverse=True,
    )
    total = sum((e["amount"] for e in charges.values()), Decimal("0"))

    card, _problem = rate_card()
    return {
        "space_id": space_id,
        "month": asked,
        "currency": settings.RATE_CARD_CURRENCY,
        "rate_card_version": card.version,
        "rows": rows,
        "total": str(total),
        "billing": (
            "Shown per person and per room. The invoice charges each run "
            "once, to the person or their project — a space is a place, "
            "not a payer."
        ),
    }


class MessageIn(BaseModel):
    """Request body for posting a message to a room."""

    body: str
    reply_to: str | None = None


class ReactionIn(BaseModel):
    """Request body adding or removing a reaction."""

    emoji: str


class PinIn(BaseModel):
    """Request body pinning or unpinning a message."""

    pinned: bool = True


def _refused(exc: Exception) -> JSONResponse:
    """A 400 response carrying the reason."""
    return JSONResponse(
        status_code=400, content={"error": "bad_request", "message": str(exc)}
    )


@router.get(
    "/{space_id}/messages",
    response_model=None,
    responses={200: {"model": TimelineOut}},
)
async def read_timeline(
    request: Request, space_id: str, after_seq: int = 0, limit: int = timeline.PAGE
) -> dict[str, Any] | JSONResponse:
    """The room, from `after_seq` onwards, oldest first (E33-T2)."""
    who = await _whoami(request)
    try:
        return await timeline.read(
            space_id, caller=who, after_seq=after_seq, limit=limit
        )
    except SpaceNotFound:
        return _NOT_FOUND


STREAM_TICK_SECONDS = 1.0

STREAM_HEARTBEAT_SECONDS = 15.0

STREAM_MAX_SECONDS = 30 * 60


@router.get(
    "/{space_id}/stream",
    response_model=None,
    response_class=EventStreamResponse,
    responses={
        200: {
            "description": (
                "Server-sent events: `open`, then `message` per message, "
                "`end` when the stream closes or membership is revoked."
            )
        }
    },
)
async def stream_timeline(request: Request, space_id: str, after_seq: int = 0) -> Any:
    """The room, pushed rather than polled (E33-T2)."""
    who, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND

    import asyncio
    import json
    import time

    from fastapi.responses import StreamingResponse

    async def events() -> Any:
        """Yield timeline events as they arrive, until the client goes away."""
        cursor = after_seq
        started = time.monotonic()
        silent = 0.0
        yield f"event: open\ndata: {json.dumps({'after_seq': cursor})}\n\n"
        while True:
            if await request.is_disconnected():
                return
            if time.monotonic() - started > STREAM_MAX_SECONDS:
                yield f"event: end\ndata: {json.dumps({'next_seq': cursor})}\n\n"
                return
            try:
                page = await timeline.read(space_id, caller=who, after_seq=cursor)
            except SpaceNotFound:
                yield 'event: end\ndata: {"reason": "not_a_member"}\n\n'
                return
            for message in page["messages"]:
                yield f"event: message\ndata: {json.dumps(message)}\n\n"
            if page["messages"]:
                cursor = page["next_seq"]
                silent = 0.0
            else:
                silent += STREAM_TICK_SECONDS
                if silent >= STREAM_HEARTBEAT_SECONDS:
                    yield ": still here\n\n"
                    silent = 0.0
            await asyncio.sleep(STREAM_TICK_SECONDS)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{space_id}/messages",
    response_model=None,
    responses={200: {"model": MessageOut}},
)
async def post_message(
    request: Request, space_id: str, body: MessageIn
) -> dict[str, Any] | JSONResponse:
    """Say something in the room."""
    who = await _whoami(request)
    try:
        return await timeline.post(
            space_id, author=who, body=body.body, reply_to=body.reply_to
        )
    except SpaceNotFound:
        return _NOT_FOUND
    except SpaceRefused as exc:
        return _refused(exc)


@router.post(
    "/{space_id}/messages/{message_id}/reactions",
    response_model=None,
    responses={200: {"model": ReactionAddedOut}},
)
async def add_reaction(
    request: Request, space_id: str, message_id: str, body: ReactionIn
) -> dict[str, Any] | JSONResponse:
    """React to a message. The same reaction twice is one reaction."""
    who = await _whoami(request)
    try:
        return await timeline.react(
            message_id, space_id=space_id, caller=who, emoji=body.emoji
        )
    except SpaceNotFound:
        return _NOT_FOUND
    except SpaceRefused as exc:
        return _refused(exc)


@router.delete(
    "/{space_id}/messages/{message_id}/reactions/{emoji}",
    response_model=None,
    responses={200: {"model": ReactionRemovedOut}},
)
async def remove_reaction(
    request: Request, space_id: str, message_id: str, emoji: str
) -> dict[str, Any] | JSONResponse:
    """Take back your own reaction — never anybody else's."""
    who = await _whoami(request)
    try:
        return await timeline.unreact(
            message_id, space_id=space_id, caller=who, emoji=emoji
        )
    except SpaceNotFound:
        return _NOT_FOUND


@router.post(
    "/{space_id}/messages/{message_id}/pin",
    response_model=None,
    responses={200: {"model": MessageOut}},
)
async def pin_message(
    request: Request, space_id: str, message_id: str, body: PinIn
) -> dict[str, Any] | JSONResponse:
    """Pin or unpin a message. Any member may: a pin is the room's."""
    who = await _whoami(request)
    try:
        return await timeline.set_pin(
            message_id, space_id=space_id, caller=who, pinned=body.pinned
        )
    except SpaceNotFound:
        return _NOT_FOUND


@router.get(
    "/{space_id}/pins", response_model=None, responses={200: {"model": PinsOut}}
)
async def read_pins(request: Request, space_id: str) -> dict[str, Any] | JSONResponse:
    """What the room has bookmarked, newest pin first."""
    who = await _whoami(request)
    try:
        return await timeline.pins(space_id, caller=who)
    except SpaceNotFound:
        return _NOT_FOUND


@router.post(
    "/{space_id}/addressed",
    response_model=None,
    responses={200: {"model": AddressedOut}},
)
async def would_answer(
    request: Request, space_id: str, body: Addressed
) -> dict[str, Any] | JSONResponse:
    """Would the agent answer this message here?"""
    _, found = await _member_or_404(request, space_id)
    if found is None:
        return _NOT_FOUND

    from agent.src.agent.config import agent_config

    handle = (agent_config.get_orchestrator_config() or {}).get("name") or "agent"
    verdict = addresses_agent(body.text, handle=handle, always_on=found.always_on)
    return {
        "addressed": verdict.addressed,
        "reason": verdict.reason,
        "handle": handle,
    }
