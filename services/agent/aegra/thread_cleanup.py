"""Thread deletion with full data cleanup."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

thread_cleanup_router = APIRouter(tags=["threads"])


async def _delete_pg_data(
    thread_id: str, user_id: str | None, conn: Any
) -> dict[str, int]:
    """Delete all PostgreSQL data for a thread within an existing transaction."""
    counts: dict[str, int] = {}

    checkpoint_total = 0
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        cur = await conn.execute(
            f"DELETE FROM {table} WHERE thread_id = %s",
            (thread_id,),
        )
        checkpoint_total += cur.rowcount
    counts["checkpoints"] = checkpoint_total

    cur = await conn.execute(
        "DELETE FROM message_feedback WHERE thread_id = %s",
        (thread_id,),
    )
    counts["feedback"] = cur.rowcount

    if user_id is not None:
        await conn.execute(
            "DELETE FROM runs WHERE thread_id = %s AND user_id = %s",
            (thread_id, user_id),
        )
        await conn.execute(
            "DELETE FROM thread WHERE thread_id = %s AND user_id = %s",
            (thread_id, user_id),
        )
    else:
        await conn.execute(
            "DELETE FROM runs WHERE thread_id = %s",
            (thread_id,),
        )
        await conn.execute(
            "DELETE FROM thread WHERE thread_id = %s",
            (thread_id,),
        )

    return counts


async def _delete_token_usage(thread_id: str) -> bool:
    """Delete token usage records for a thread from MongoDB (best-effort)."""
    if not settings.MONGODB_URI:
        return False

    from agent.src.token_budget.service import _mongo_repo

    repo = _mongo_repo()
    result = await repo._thread_collection().delete_many({"thread_id": thread_id})
    return bool(result.deleted_count > 0)


def _session_document_store() -> Any:
    """The document store, when this deployment keeps one."""
    from agent.src.agent.config import agent_config

    try:
        if not agent_config.get_knowledge_config().enabled:
            return None
    except Exception:
        return None

    from agent.src.knowledge.store import session_store

    return session_store()


async def _forget_thread_documents(thread_id: str, *, store: Any = None) -> bool:
    """Drop the conversation's documents."""
    if store is None:
        return False
    try:
        store.forget_thread(thread_id)
        return True
    except Exception:
        logger.warning(
            "thread_documents_cleanup_failed", thread_id=thread_id, exc_info=True
        )
        return False


class ThreadDeletedOut(BaseModel):
    """What a thread deletion removed, counted per store."""

    status: str


@thread_cleanup_router.delete(
    "/threads/{thread_id}", responses={200: {"model": ThreadDeletedOut}}
)
async def delete_thread_with_cleanup(
    thread_id: str, request: Request
) -> dict[str, Any]:
    """Delete a thread and purge all associated data."""
    from uuid import UUID

    try:
        UUID(thread_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid thread_id format"
        ) from None

    from agent.aegra.auth import ENABLE_AUTH

    user_id: str | None = None
    if ENABLE_AUTH:
        user_id = await authenticated_user_id(request, reject_anonymous=True)

    if not settings.database_uri:
        raise HTTPException(status_code=503, detail="Database unavailable")

    import psycopg

    async with await psycopg.AsyncConnection.connect(settings.database_uri) as conn:
        if user_id is not None:
            cur = await conn.execute(
                "SELECT thread_id FROM thread "
                "WHERE thread_id = %s AND user_id = %s FOR UPDATE",
                (thread_id, user_id),
            )
        else:
            cur = await conn.execute(
                "SELECT thread_id FROM thread WHERE thread_id = %s FOR UPDATE",
                (thread_id,),
            )
        thread = await cur.fetchone()

        if not thread:
            raise HTTPException(
                status_code=404, detail=f"Thread '{thread_id}' not found"
            )

        counts = await _delete_pg_data(thread_id, user_id, conn)
        await conn.commit()

    token_usage_deleted = False
    try:
        token_usage_deleted = await _delete_token_usage(thread_id)
    except Exception:
        logger.warning(
            "token_usage_cleanup_failed_after_pg_commit",
            thread_id=thread_id,
            exc_info=True,
        )

    documents_deleted = await _forget_thread_documents(
        thread_id, store=_session_document_store()
    )

    logger.info(
        "thread_deleted_with_cleanup",
        thread_id=thread_id,
        user_id=user_id[:8] if user_id else "no-auth",
        checkpoints_deleted=counts["checkpoints"],
        feedback_deleted=counts["feedback"],
        token_usage_deleted=token_usage_deleted,
        documents_deleted=documents_deleted,
    )

    return {"status": "deleted"}
