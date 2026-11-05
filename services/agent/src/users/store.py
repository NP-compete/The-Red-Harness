"""Where profile overrides are kept (E9-T2)."""

from __future__ import annotations

import asyncio
from typing import Any

from agent.src.users.profiles import CREATE_PROFILES_TABLE, PROFILE_FIELDS
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_ensured = False
_lock = asyncio.Lock()


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
            await conn.execute(CREATE_PROFILES_TABLE)
        _ensured = True


async def load_profile(user_id: str) -> dict[str, str]:
    """The overrides held for this person — empty when there are none."""
    await _ensure_table()
    from agent.src.db.pool import connection

    columns = ", ".join(PROFILE_FIELDS)
    async with connection() as conn:
        cursor = await conn.execute(
            f"SELECT {columns} FROM user_profiles WHERE user_id = %s",  # noqa: S608
            (user_id,),
        )
        row = await cursor.fetchone()
    if not row:
        return {}
    return {name: row[name] for name in PROFILE_FIELDS if row[name]}


async def save_profile(
    user_id: str, changes: dict[str, str], *, updated_by: str
) -> dict[str, Any]:
    """Apply the changes and hand back what the row now says."""
    await _ensure_table()
    from agent.src.db.pool import connection

    names = [n for n in PROFILE_FIELDS if n in changes]
    assignments = ", ".join(f"{n} = EXCLUDED.{n}" for n in names)
    placeholders = ", ".join(["%s"] * len(names))
    statement = (
        f"INSERT INTO user_profiles (user_id, {', '.join(names)}, updated_by) "  # noqa: S608
        f"VALUES (%s, {placeholders}, %s) "
        f"ON CONFLICT (user_id) DO UPDATE SET {assignments}, "
        "updated_by = EXCLUDED.updated_by, updated_at = now()"
    )
    values = [user_id, *[changes[n] for n in names], updated_by]

    async with connection() as conn:
        await conn.execute(statement, values)

    return {
        "user_id": user_id,
        "fields": await load_profile(user_id),
        "updated_by": updated_by,
        "applies": "immediately",
    }
