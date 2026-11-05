"""Where spaces are kept (E33-T1)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from agent.src.spaces.errors import SpaceRefused
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

MAX_NAME = 120

CREATE_SPACES_TABLE = """
CREATE TABLE IF NOT EXISTS spaces (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    group_cn      TEXT NOT NULL,
    created_by    TEXT NOT NULL,
    always_on     BOOLEAN NOT NULL DEFAULT FALSE,
    active_run_id TEXT,
    active_run_by TEXT,
    active_run_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_spaces_group_cn ON spaces (group_cn);
"""

_ensured = False
_lock = asyncio.Lock()


@dataclass(frozen=True)
class Space:
    """One space, as stored."""

    space_id: str
    name: str
    group_cn: str
    created_by: str
    created_at: str | None = None
    always_on: bool = False

    def as_dict(self) -> dict[str, Any]:
        """The space as a plain dictionary."""
        return {
            "space_id": self.space_id,
            "name": self.name,
            "group_cn": self.group_cn,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "always_on": self.always_on,
        }


async def _ensure_table() -> None:
    """Create the table once, however many callers arrive together."""
    global _ensured  # noqa: PLW0603
    if _ensured:
        return
    async with _lock:
        if globals()["_ensured"]:
            return
        from agent.src.db.pool import connection

        async with connection() as conn:
            await conn.execute(CREATE_SPACES_TABLE)
        _ensured = True


def validate(name: str, group_cn: str) -> tuple[str, str]:
    """A space that can be found and whose membership can be answered."""
    name = (name or "").strip()
    group = (group_cn or "").strip()
    if not name:
        raise SpaceRefused("a space needs a name")
    if len(name) > MAX_NAME:
        raise SpaceRefused(f"the name is over {MAX_NAME} characters")
    if not group:
        raise SpaceRefused(
            "a space needs the name of a directory group — membership comes "
            "from the identity provider, so a room with no group has no "
            "members and no way to gain any"
        )
    return name, group


async def create(*, name: str, group_cn: str, created_by: str) -> Space:
    """Create a space owned by `created_by` and return it."""
    name, group_cn = validate(name, group_cn)
    await _ensure_table()
    from agent.src.db.pool import connection

    space_id = str(uuid.uuid4())
    async with connection() as conn:
        await conn.execute(
            "INSERT INTO spaces (id, name, group_cn, created_by) "
            "VALUES (%s, %s, %s, %s)",
            (space_id, name, group_cn, created_by),
        )
    logger.warning(
        "Space created: %s (%s) by %s, members from %s",
        name,
        space_id,
        created_by,
        group_cn,
    )
    return await get(space_id) or Space(space_id, name, group_cn, created_by)


async def get(space_id: str) -> Space | None:
    """The space with this id, or `None` if there is none."""
    await _ensure_table()
    from agent.src.db.pool import connection

    async with connection() as conn:
        cursor = await conn.execute(
            "SELECT id::text, name, group_cn, created_by, "
            "created_at::text, always_on FROM spaces WHERE id = %s",
            (space_id,),
        )
        row = await cursor.fetchone()
    if not row:
        return None
    return Space(
        row["id"],
        row["name"],
        row["group_cn"],
        row["created_by"],
        row["created_at"],
        row["always_on"],
    )


async def all_spaces() -> list[Space]:
    """Every space, before membership is applied."""
    await _ensure_table()
    from agent.src.db.pool import connection

    async with connection() as conn:
        cursor = await conn.execute(
            "SELECT id::text, name, group_cn, created_by, "
            "created_at::text, always_on FROM spaces ORDER BY created_at"
        )
        rows = await cursor.fetchall()
    return [
        Space(
            r["id"],
            r["name"],
            r["group_cn"],
            r["created_by"],
            r["created_at"],
            r["always_on"],
        )
        for r in rows
    ]


@dataclass(frozen=True)
class ActiveRun:
    """The run currently holding a space."""

    run_id: str
    triggered_by: str
    at: str | None = None


class SpaceBusy(RuntimeError):
    """Somebody else's run is already going in this room."""

    def __init__(self, holder: str) -> None:
        """Record who holds the space and explain when the slot frees."""
        self.holder = holder
        super().__init__(
            f"{holder} has a run going in this space. One at a time, so two "
            "people cannot act on the same conversation at once. The slot "
            f"frees itself {STALE_RUN_AFTER_SECONDS // 60} minutes after it "
            "was taken, so a run that died does not wedge the room."
        )


STALE_RUN_AFTER_SECONDS = 15 * 60


async def claim_run(space_id: str, *, run_id: str, by: str) -> ActiveRun:
    """Take the room's single run slot, or raise if it is taken."""
    await _ensure_table()
    from agent.src.db.pool import connection

    async with connection() as conn:
        cursor = await conn.execute(
            "UPDATE spaces SET active_run_id = %s, active_run_by = %s, "
            "active_run_at = now() WHERE id = %s AND (active_run_id IS NULL "
            "OR active_run_at < now() - make_interval(secs => %s)) "
            "RETURNING active_run_id, active_run_by, active_run_at::text",
            (run_id, by, space_id, STALE_RUN_AFTER_SECONDS),
        )
        row = await cursor.fetchone()
        if row:
            return ActiveRun(
                row["active_run_id"], row["active_run_by"], row["active_run_at"]
            )

        held = await conn.execute(
            "SELECT active_run_by FROM spaces WHERE id = %s", (space_id,)
        )
        current = await held.fetchone()

    raise SpaceBusy((current or {}).get("active_run_by") or "somebody")


async def release_run(space_id: str, *, run_id: str) -> None:
    """Give the slot back, but only for the run that holds it."""
    await _ensure_table()
    from agent.src.db.pool import connection

    async with connection() as conn:
        await conn.execute(
            "UPDATE spaces SET active_run_id = NULL, active_run_by = NULL, "
            "active_run_at = NULL WHERE id = %s AND active_run_id = %s",
            (space_id, run_id),
        )


async def active_run(space_id: str) -> ActiveRun | None:
    """What is going on in this room, if anything."""
    await _ensure_table()
    from agent.src.db.pool import connection

    async with connection() as conn:
        cursor = await conn.execute(
            "SELECT active_run_id, active_run_by, active_run_at::text "
            "FROM spaces WHERE id = %s",
            (space_id,),
        )
        row = await cursor.fetchone()
    if not row or not row["active_run_id"]:
        return None
    return ActiveRun(row["active_run_id"], row["active_run_by"], row["active_run_at"])


async def set_always_on(space_id: str, *, always_on: bool) -> bool:
    """Whether the agent answers every message in this room (E33-T3)."""
    await _ensure_table()
    from agent.src.db.pool import connection

    async with connection() as conn:
        cursor = await conn.execute(
            "UPDATE spaces SET always_on = %s WHERE id = %s RETURNING id",
            (always_on, space_id),
        )
        return await cursor.fetchone() is not None
