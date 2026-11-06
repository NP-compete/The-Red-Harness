"""Creating a conversation on somebody's behalf, so they can find it."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


def title_from(instruction: str, *, limit: int = 60) -> str:
    """A one-line name a person will recognise in a list."""
    flat = " ".join(instruction.split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


async def inherited_identity(session: Any) -> str | None:
    """`user_identity` from the conversation this work was asked for in."""
    from agent.src.token_budget.identity import resolve_thread_id

    asked_in = resolve_thread_id()
    if not asked_in:
        return None
    try:
        from aegra_api.core.orm import Thread as ThreadORM

        found = await session.get(ThreadORM, asked_in)
    except Exception:  # noqa: BLE001 — a missing parent is not fatal
        return None
    identity = ((getattr(found, "metadata_json", None) or {}) or {}).get(
        "user_identity"
    )
    return str(identity) if identity else None


async def create_owned_thread(
    session: Any,
    *,
    owner: str,
    title: str,
    extra: dict[str, Any] | None = None,
) -> str:
    """A new thread owned by *owner* and findable by the interface."""
    from aegra_api.core.orm import Thread as ThreadORM

    thread_id = str(uuid4())
    metadata: dict[str, Any] = {
        "owner": owner,
        "assistant_id": None,
        "graph_id": None,
        "thread_name": title,
        **(extra or {}),
    }
    identity = await inherited_identity(session)
    if identity:
        metadata["user_identity"] = identity

    session.add(
        ThreadORM(
            thread_id=thread_id,
            status="idle",
            metadata_json=metadata,
            user_id=owner,
        )
    )
    await session.flush()
    return thread_id
