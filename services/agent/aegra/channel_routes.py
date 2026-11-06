"""Inbound channel endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.channels.adapters import AdapterError, InboundMessage, parse
from agent.src.channels.config import ChannelConfig
from agent.src.channels.dispatch import (
    already_handled,
    deliver,
    run_for_channel,
)
from agent.src.channels.signatures import verify_slack, verify_webhook
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/channels", tags=["channels"])

_BACKGROUND_TASKS: set[asyncio.Task[None]] = set()


def _load_channels() -> dict[str, ChannelConfig]:
    """Active channels, re-read per request so config can hot-reload."""
    from agent.src.channels.loader import load_channels

    return load_channels().active()


def _delivery_key(request: Request, body: bytes) -> str:
    """A stable id for this exact delivery, for payloads carrying none."""
    signature = request.headers.get("X-Slack-Signature") or request.headers.get(
        "X-Signature", ""
    )
    if signature:
        return "sig:" + hashlib.sha256(signature.encode()).hexdigest()
    timestamp = (
        request.headers.get("X-Slack-Request-Timestamp")
        or request.headers.get("X-Timestamp")
        or ""
    )
    return "body:" + hashlib.sha256(timestamp.encode() + b"\0" + body).hexdigest()


def _verify(channel: ChannelConfig, request: Request, body: bytes) -> None:
    """Raise 401 unless the request is authentically from this channel."""
    secret = channel.signing_secret
    if not secret:
        logger.error(
            "Channel %s has no secret in %s", channel.type, channel.signing_secret_env
        )
        raise HTTPException(status_code=401, detail="Signature verification failed")

    if channel.type == "slack":
        result = verify_slack(
            body=body,
            timestamp=request.headers.get("X-Slack-Request-Timestamp", ""),
            signature=request.headers.get("X-Slack-Signature", ""),
            secret=secret,
            max_age_seconds=channel.max_age_seconds,
        )
    else:
        result = verify_webhook(
            body=body,
            timestamp=request.headers.get("X-Timestamp", ""),
            signature=request.headers.get("X-Signature", ""),
            secret=secret,
            max_age_seconds=channel.max_age_seconds,
        )

    if not result:
        logger.warning("Channel signature rejected: %s", result.reason)
        raise HTTPException(status_code=401, detail="Signature verification failed")


async def _run_and_deliver(
    message: InboundMessage, channel: ChannelConfig, user_id: str
) -> None:
    """Background half of ack-then-work."""
    try:
        reply = await run_for_channel(
            message,
            channel,
            user_id,
            service_token=os.environ.get("CHANNEL_SERVICE_TOKEN"),
        )
        await deliver(reply, message, channel)
    except Exception:
        logger.exception("Channel run failed for conversation %s", message.conversation)


class ChannelOut(BaseModel):
    """One inbound channel: what it is and whether it is on."""

    name: str
    type: str
    assistant_id: str | None = None


class ChannelListOut(BaseModel):
    """Every inbound channel this deployment declares."""

    channels: list[ChannelOut]


class ChallengeOut(BaseModel):
    """The handshake a provider sends before it will deliver."""

    challenge: str


@router.post("/{name}", responses={200: {"model": ChallengeOut}})
async def receive(name: str, request: Request) -> Response:
    """Accept an event from a configured channel."""
    channels = _load_channels()
    channel = channels.get(name)
    if channel is None:
        raise HTTPException(status_code=404, detail="Unknown channel")

    body = await request.body()
    _verify(channel, request, body)

    try:
        payload: dict[str, Any] = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Body is not JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body is not a JSON object")

    if payload.get("type") == "url_verification":
        return Response(
            content=json.dumps({"challenge": payload.get("challenge", "")}),
            media_type="application/json",
        )

    try:
        message = parse(channel.type, payload)
    except AdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    if message is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    event_key = message.metadata.get("event_id") or _delivery_key(request, body)
    if await already_handled(event_key):
        logger.info("Ignoring duplicate delivery of %s", event_key)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    user_id = channel.identity.resolve(message.sender)
    if user_id is None:
        logger.warning("Channel %s rejected unmapped sender %s", name, message.sender)
        raise HTTPException(status_code=403, detail="Sender is not authorised")

    task = asyncio.create_task(_run_and_deliver(message, channel, user_id))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.get("/", responses={200: {"model": ChannelListOut}})
async def list_channels(request: Request) -> dict[str, Any]:
    """Which channels are live. No secrets, no identity maps."""
    await authenticated_user_id(request, reject_anonymous=True)
    return {
        "channels": [
            {"name": name, "type": c.type, "assistant_id": c.assistant_id}
            for name, c in _load_channels().items()
        ]
    }
