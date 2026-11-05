"""Run the agent on behalf of a channel, then deliver the answer."""

from __future__ import annotations

import asyncio
import hashlib
from collections import OrderedDict
from typing import Any

import httpx

from agent.src.channels.adapters import InboundMessage
from agent.src.channels.config import ChannelConfig
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_SEEN_EVENTS: dict[str, float] = {}
_SEEN_LIMIT = settings.CHANNEL_SEEN_LIMIT


def _base_url() -> str:
    return settings.loopback_base_url


_SEEN_TTL_SECONDS = 900


async def already_handled(event_key: str) -> bool:
    """True if this exact delivery has been seen before."""
    if not event_key:
        return False

    from agent.aegra.redis import claim_once, run_redis

    mine = await run_redis(
        claim_once, f"channel:seen:{event_key}", ttl_seconds=_SEEN_TTL_SECONDS
    )
    if mine is False:
        return True
    if event_key in _SEEN_EVENTS:
        return True

    loop_time = asyncio.get_event_loop().time()
    if len(_SEEN_EVENTS) >= _SEEN_LIMIT:
        oldest = sorted(_SEEN_EVENTS, key=_SEEN_EVENTS.__getitem__)[: _SEEN_LIMIT // 2]
        for key in oldest:
            _SEEN_EVENTS.pop(key, None)
    _SEEN_EVENTS[event_key] = loop_time
    return False


def thread_key(conversation: str) -> str:
    """Deterministic agent thread id for a conversation."""
    digest = hashlib.sha256(conversation.encode()).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"
    )


async def _ensure_thread(client: httpx.AsyncClient, thread_id: str) -> None:
    """Create the thread if this is the first message in the conversation."""
    existing = await client.get(f"/threads/{thread_id}")
    if existing.status_code == 200:
        return
    created = await client.post("/threads", json={"thread_id": thread_id})
    if created.status_code not in (200, 201, 409):
        created.raise_for_status()


async def run_for_channel(
    message: InboundMessage,
    channel: ChannelConfig,
    user_id: str,
    *,
    service_token: str | None = None,
) -> str:
    """Run the agent and return its reply text."""
    headers: dict[str, str] = {}
    if service_token:
        headers["Authorization"] = f"Bearer {service_token}"
    headers["X-Channel-User-Id"] = user_id

    thread_id = thread_key(message.conversation)

    async with httpx.AsyncClient(
        base_url=_base_url(), headers=headers, timeout=channel.timeout_seconds
    ) as client:
        await _ensure_thread(client, thread_id)

        response = await client.post(
            f"/threads/{thread_id}/runs/wait",
            json={
                "assistant_id": channel.assistant_id,
                "input": {"messages": [{"type": "human", "content": message.text}]},
            },
        )
        response.raise_for_status()
        return _reply_text(response.json())


def _content_text(content: Any) -> str:
    """Flatten a message's content to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ]
        return "\n".join(p for p in parts if p.strip())
    return ""


def _reply_text(payload: Any) -> str:
    """Pull the assistant's last message out of a run result."""
    messages = (payload or {}).get("messages") or []
    for message in reversed(messages):
        if message.get("type") == "ai":
            text = _content_text(message.get("content"))
            if text:
                return text
    error = (payload or {}).get("__error__")
    if error:
        return f"The agent could not complete that: {error.get('message', 'unknown error')}"
    return "The agent produced no reply."


_DELIVERED: OrderedDict[str, None] = OrderedDict()
_REMEMBER = 1024

_DELIVERED_TTL_SECONDS = 3600


async def _already_delivered(key: str) -> bool:
    """Has this exact answer already gone out — from any pod?"""
    from agent.aegra.redis import claim_once, run_redis

    mine = await run_redis(
        claim_once, f"channel:sent:{key}", ttl_seconds=_DELIVERED_TTL_SECONDS
    )
    if mine is None:
        return key in _DELIVERED
    return not mine


async def _forget_delivery(key: str) -> None:
    """Give the claim back when the delivery did not arrive."""
    from agent.aegra.redis import cache_delete, run_redis

    _DELIVERED.pop(key, None)
    await run_redis(cache_delete, f"channel:sent:{key}")


def _delivery_key(reply: str, message: InboundMessage) -> str:
    """What makes this delivery the same as an earlier one."""
    event = str((message.metadata or {}).get("event_id") or "").strip()
    answer = hashlib.sha256(reply.encode("utf-8")).hexdigest()[:16]
    return f"{event or message.conversation}:{answer}"


async def deliver(reply: str, message: InboundMessage, channel: ChannelConfig) -> None:
    """Post the answer back to wherever it came from, once."""
    key = _delivery_key(reply, message)
    if await _already_delivered(key):
        logger.info(
            "Skipping a repeat delivery for conversation %s", message.conversation
        )
        return

    if channel.type == "slack":
        arrived = await _deliver_slack(reply, message)
    elif message.reply_to:
        arrived = await _deliver_webhook(reply, message)
    else:
        return

    if not arrived:
        logger.warning(
            "Delivery to conversation %s did not arrive — not remembering it, "
            "so a retry still can",
            message.conversation,
        )
        await _forget_delivery(key)
        return

    _DELIVERED[key] = None
    while len(_DELIVERED) > _REMEMBER:
        _DELIVERED.popitem(last=False)


async def _deliver_slack(reply: str, message: InboundMessage) -> bool:
    from agent.src.security.secret_source import (
        SecretUnavailable,
        from_variable,
    )

    try:
        token = from_variable("SLACK_BOT_TOKEN")
    except SecretUnavailable as missing:
        logger.warning("Cannot post reply: %s", missing)
        return False
    if not token:
        logger.warning("SLACK_BOT_TOKEN unset — cannot post reply")
        return False

    async with httpx.AsyncClient(timeout=30) as client:
        result = await client.post(
            settings.SLACK_POST_MESSAGE_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "channel": message.metadata.get("channel"),
                "thread_ts": message.metadata.get("thread_ts"),
                "text": reply,
            },
        )
        body = result.json()
        if not body.get("ok"):
            logger.warning("Slack rejected the reply: %s", body.get("error"))
            return False
    return True


async def _deliver_webhook(reply: str, message: InboundMessage) -> bool:
    """POST the reply to the sender's callback URL."""
    from agent.src.knowledge.fetch import UnsafeURLError, assert_safe_url

    url = str(message.reply_to)
    try:
        await asyncio.to_thread(assert_safe_url, url)
    except UnsafeURLError as exc:
        logger.warning("Refusing callback to %s: %s", url, exc)
        return False

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            answered = await client.post(
                url,
                json={"conversation": message.conversation, "text": reply},
            )
        except httpx.HTTPError as exc:
            logger.warning("Callback to %s failed: %s", message.reply_to, exc)
            return False
        if answered.is_error:
            logger.warning(
                "Callback to %s answered %d", message.reply_to, answered.status_code
            )
            return False
    return True
