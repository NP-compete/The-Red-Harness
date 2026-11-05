"""The timeline a space is: messages, replies, reactions and pins (E33-T2)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from agent.src.spaces.errors import SpaceNotFound, SpaceRefused
from agent.src.spaces.membership import is_member
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

MAX_BODY = 32_000
MAX_EMOJI = 32
PAGE = 200

CREATE_TIMELINE_TABLES = """
CREATE TABLE IF NOT EXISTS space_messages (
    seq        BIGSERIAL PRIMARY KEY,
    id         UUID NOT NULL UNIQUE,
    space_id   UUID NOT NULL,
    author     TEXT NOT NULL,
    body       TEXT NOT NULL,
    reply_to   UUID,
    pinned_by  TEXT,
    pinned_at  TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_space_messages_space_seq
    ON space_messages (space_id, seq);
CREATE INDEX IF NOT EXISTS idx_space_messages_reply
    ON space_messages (reply_to) WHERE reply_to IS NOT NULL;

CREATE TABLE IF NOT EXISTS space_reactions (
    message_id UUID NOT NULL,
    reactor    TEXT NOT NULL,
    emoji      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (message_id, reactor, emoji)
);
"""

_ensured = False
_lock = asyncio.Lock()


async def _ensure_tables() -> None:
    """Create them once, however many callers arrive together."""
    global _ensured  # noqa: PLW0603
    if _ensured:
        return
    async with _lock:
        if globals()["_ensured"]:
            return
        from agent.src.db.pool import connection

        async with connection() as conn:
            await conn.execute(CREATE_TIMELINE_TABLES)
        _ensured = True


async def _group_of(conn: Any, space_id: str) -> str:
    cursor = await conn.execute(
        "SELECT group_cn FROM spaces WHERE id = %s", (space_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise SpaceNotFound("No such space.")
    return str(row["group_cn"])


async def _require_member(conn: Any, space_id: str, caller: str) -> None:
    """404 for an outsider, here as in `store` — the room's name leaks."""
    group = await _group_of(conn, space_id)
    if not await is_member(caller, group):
        raise SpaceNotFound("No such space.")


def _message(
    row: dict[str, Any], reactions: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    created = row["created_at"]
    return {
        "seq": row["seq"],
        "id": str(row["id"]),
        "space_id": str(row["space_id"]),
        "author": row["author"],
        "body": row["body"],
        "reply_to": str(row["reply_to"]) if row["reply_to"] else None,
        "pinned": bool(row["pinned_by"]),
        "pinned_by": row["pinned_by"],
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
        "reactions": reactions or {},
    }


async def post(
    space_id: str, *, author: str, body: str, reply_to: str | None = None
) -> dict[str, Any]:
    """Add a message, returning it with the sequence it was given."""
    body = (body or "").strip()
    if not body:
        raise SpaceRefused("A message needs something in it.")
    if len(body) > MAX_BODY:
        raise SpaceRefused(f"A message may be at most {MAX_BODY} characters.")

    await _ensure_tables()
    from agent.src.db.pool import connection

    async with connection() as conn:
        await _require_member(conn, space_id, author)
        if reply_to is not None:
            cursor = await conn.execute(
                "SELECT 1 FROM space_messages WHERE id = %s AND space_id = %s",
                (reply_to, space_id),
            )
            if await cursor.fetchone() is None:
                raise SpaceRefused("That message is not in this space.")
        cursor = await conn.execute(
            "INSERT INTO space_messages (id, space_id, author, body, reply_to) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (str(uuid.uuid4()), space_id, author, body, reply_to),
        )
        row = await cursor.fetchone()
    return _message(row)


async def read(
    space_id: str, *, caller: str, after_seq: int = 0, limit: int = PAGE
) -> dict[str, Any]:
    """A page of the timeline from *after_seq*, oldest first."""
    limit = max(1, min(int(limit), PAGE))
    await _ensure_tables()
    from agent.src.db.pool import connection

    async with connection() as conn:
        await _require_member(conn, space_id, caller)
        cursor = await conn.execute(
            "SELECT * FROM space_messages WHERE space_id = %s AND seq > %s "
            "ORDER BY seq LIMIT %s",
            (space_id, after_seq, limit),
        )
        rows = await cursor.fetchall()
        reactions: dict[str, dict[str, list[str]]] = {}
        if rows:
            cursor = await conn.execute(
                "SELECT message_id, emoji, reactor FROM space_reactions "
                "WHERE message_id = ANY(%s) ORDER BY created_at",
                ([r["id"] for r in rows],),
            )
            for r in await cursor.fetchall():
                key = str(r["message_id"])
                reactions.setdefault(key, {}).setdefault(r["emoji"], []).append(
                    r["reactor"]
                )
    messages = [_message(r, reactions.get(str(r["id"]), {})) for r in rows]
    return {
        "messages": messages,
        "next_seq": messages[-1]["seq"] if messages else after_seq,
    }


async def _message_in(conn: Any, message_id: str, space_id: str) -> None:
    """The message exists, is in this room, and the caller may be here."""
    cursor = await conn.execute(
        "SELECT 1 FROM space_messages WHERE id = %s AND space_id = %s",
        (message_id, space_id),
    )
    if await cursor.fetchone() is None:
        raise SpaceNotFound("No such message.")


async def react(
    message_id: str, *, space_id: str, caller: str, emoji: str
) -> dict[str, Any]:
    """Add a reaction. Reacting twice the same way is one reaction."""
    emoji = (emoji or "").strip()
    if not emoji or len(emoji) > MAX_EMOJI:
        raise SpaceRefused("A reaction needs a short emoji.")
    await _ensure_tables()
    from agent.src.db.pool import connection

    async with connection() as conn:
        await _require_member(conn, space_id, caller)
        await _message_in(conn, message_id, space_id)
        await conn.execute(
            "INSERT INTO space_reactions (message_id, reactor, emoji) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (message_id, caller, emoji),
        )
    return {"message_id": message_id, "emoji": emoji, "reactor": caller}


async def unreact(
    message_id: str, *, space_id: str, caller: str, emoji: str
) -> dict[str, Any]:
    """Remove the caller's own reaction. Never anybody else's."""
    await _ensure_tables()
    from agent.src.db.pool import connection

    async with connection() as conn:
        await _require_member(conn, space_id, caller)
        await conn.execute(
            "DELETE FROM space_reactions WHERE message_id = %s AND reactor = %s "
            "AND emoji = %s",
            (message_id, caller, emoji),
        )
    return {"message_id": message_id, "emoji": emoji, "removed": True}


async def set_pin(
    message_id: str, *, space_id: str, caller: str, pinned: bool
) -> dict[str, Any]:
    """Pin or unpin a message."""
    await _ensure_tables()
    from agent.src.db.pool import connection

    async with connection() as conn:
        await _require_member(conn, space_id, caller)
        await _message_in(conn, message_id, space_id)
        cursor = await conn.execute(
            "UPDATE space_messages SET pinned_by = %s, "
            "pinned_at = CASE WHEN %s THEN now() ELSE NULL END "
            "WHERE id = %s RETURNING *",
            (caller if pinned else None, pinned, message_id),
        )
        updated = await cursor.fetchone()
    return _message(updated)


async def pins(space_id: str, *, caller: str) -> dict[str, Any]:
    """Everything pinned in the room, newest pin first."""
    await _ensure_tables()
    from agent.src.db.pool import connection

    async with connection() as conn:
        await _require_member(conn, space_id, caller)
        cursor = await conn.execute(
            "SELECT * FROM space_messages WHERE space_id = %s "
            "AND pinned_by IS NOT NULL ORDER BY pinned_at DESC",
            (space_id,),
        )
        rows = await cursor.fetchall()
    return {"pins": [_message(r) for r in rows]}
