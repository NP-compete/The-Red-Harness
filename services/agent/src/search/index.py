"""The `thread_search` table: build it, keep it current, query it."""

from __future__ import annotations

from typing import Any

import psycopg

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

MAX_THREADS_PER_REFRESH = settings.SEARCH_MAX_THREADS_PER_REFRESH
MAX_BODY_CHARS = settings.SEARCH_MAX_BODY_CHARS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS thread_search (
    thread_id         TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    title             TEXT NOT NULL DEFAULT '',
    body              TEXT NOT NULL DEFAULT '',
    -- Generated, so the vector can never drift from the text it indexes.
    search_vector     tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(body, '')), 'B')
    ) STORED,
    source_updated_at TIMESTAMPTZ,
    indexed_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_thread_search_vector
    ON thread_search USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_thread_search_user
    ON thread_search (user_id);
"""


def _ext_hook(code: int, data: bytes) -> Any:
    """Tolerate msgpack ext types we do not understand."""
    import msgpack

    try:
        return msgpack.unpackb(data, raw=False, ext_hook=_ext_hook)
    except Exception:
        return data


def extract_text(blob: bytes) -> str:
    """Pull searchable text out of one checkpoint blob."""
    import msgpack

    try:
        items = msgpack.unpackb(bytes(blob), raw=False, ext_hook=_ext_hook)
    except Exception:
        return ""
    if not isinstance(items, (list, tuple)):
        return ""

    parts: list[str] = []
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        message = item[2]
        if not isinstance(message, dict):
            continue
        if message.get("type") not in ("human", "ai"):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])

    return "\n".join(parts)[:MAX_BODY_CHARS]


async def ensure_schema(conn: psycopg.AsyncConnection) -> None:
    """Create the search tables if they are not there yet."""
    await conn.execute(_SCHEMA)


async def _stale_threads(
    conn: psycopg.AsyncConnection, user_id: str
) -> list[tuple[str, Any]]:
    """Threads of this user that the index has not caught up with."""
    rows = await conn.execute(
        """
        SELECT t.thread_id, t.updated_at
        FROM thread t
        LEFT JOIN thread_search s ON s.thread_id = t.thread_id
        WHERE t.user_id = %s
          AND (s.thread_id IS NULL OR s.source_updated_at IS DISTINCT FROM t.updated_at)
        ORDER BY t.updated_at DESC
        LIMIT %s
        """,
        (user_id, MAX_THREADS_PER_REFRESH),
    )
    return [(row[0], row[1]) for row in await rows.fetchall()]


async def _thread_body(conn: psycopg.AsyncConnection, thread_id: str) -> str:
    """Current conversation text for one thread."""
    chunks: list[str] = []

    blobs = await conn.execute(
        """
        SELECT DISTINCT ON (channel) blob
        FROM checkpoint_blobs
        WHERE thread_id = %s AND checkpoint_ns = '' AND channel = 'messages'
        ORDER BY channel, version DESC
        """,
        (thread_id,),
    )
    chunks += [extract_text(blob) for (blob,) in await blobs.fetchall() if blob]

    writes = await conn.execute(
        """
        SELECT blob
        FROM checkpoint_writes
        WHERE thread_id = %s AND checkpoint_ns = '' AND channel = 'messages'
        """,
        (thread_id,),
    )
    chunks += [extract_text(blob) for (blob,) in await writes.fetchall() if blob]

    seen: set[str] = set()
    unique: list[str] = []
    for chunk in chunks:
        if chunk and chunk not in seen:
            seen.add(chunk)
            unique.append(chunk)
    return "\n".join(unique)[:MAX_BODY_CHARS]


def derive_title(body: str) -> str:
    """First line of the first message, near enough to a subject line."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


async def refresh_user(user_id: str) -> int:
    """Bring this user's index entries up to date. Returns rows written."""
    written = 0
    async with await psycopg.AsyncConnection.connect(settings.database_uri) as conn:
        await ensure_schema(conn)
        stale = await _stale_threads(conn, user_id)

        for thread_id, updated_at in stale:
            body = await _thread_body(conn, thread_id)
            await conn.execute(
                """
                INSERT INTO thread_search
                    (thread_id, user_id, title, body, source_updated_at, indexed_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (thread_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    title = EXCLUDED.title,
                    body = EXCLUDED.body,
                    source_updated_at = EXCLUDED.source_updated_at,
                    indexed_at = now()
                """,
                (thread_id, user_id, derive_title(body), body, updated_at),
            )
            written += 1

        await conn.commit()

    if written:
        logger.info("Reindexed %d thread(s) for search", written)
    return written


async def search(
    user_id: str, query: str, *, limit: int = 20, offset: int = 0
) -> list[dict[str, Any]]:
    """Ranked matches for one user."""
    if not query.strip():
        return []

    async with await psycopg.AsyncConnection.connect(settings.database_uri) as conn:
        await ensure_schema(conn)
        rows = await conn.execute(
            """
            SELECT
                s.thread_id,
                s.title,
                ts_rank(s.search_vector, websearch_to_tsquery('english', %(q)s)) AS rank,
                ts_headline(
                    'english', s.body, websearch_to_tsquery('english', %(q)s),
                    'MaxFragments=2, MinWords=5, MaxWords=18, StartSel=<<, StopSel=>>'
                ) AS snippet,
                s.source_updated_at
            FROM thread_search s
            WHERE s.user_id = %(user)s
              AND s.search_vector @@ websearch_to_tsquery('english', %(q)s)
            ORDER BY rank DESC, s.source_updated_at DESC NULLS LAST
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "q": query,
                "user": user_id,
                "limit": max(1, min(limit, 100)),
                "offset": max(0, offset),
            },
        )
        return [
            {
                "thread_id": row[0],
                "title": row[1],
                "rank": float(row[2]),
                "snippet": row[3],
                "updated_at": row[4].isoformat() if row[4] else None,
            }
            for row in await rows.fetchall()
        ]
