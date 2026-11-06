"""Who is in a space, answered by the directory and nowhere else."""

from __future__ import annotations

import asyncio

import structlog

logger = structlog.get_logger(__name__)


async def is_member(user_id: str, group_cn: str) -> bool:
    """Whether *user_id* is in *group_cn*, according to the directory."""
    if not user_id or not group_cn:
        return False

    from agent.aegra.auth import ENABLE_AUTH

    if not ENABLE_AUTH:
        return True

    from agent.src.ldap.service import _is_user_in_group_sync

    try:
        return await asyncio.to_thread(_is_user_in_group_sync, user_id, group_cn)
    except Exception as exc:
        logger.warning(
            "space_membership_unavailable",
            user_id=user_id,
            group_cn=group_cn,
            error=str(exc),
        )
        return False
