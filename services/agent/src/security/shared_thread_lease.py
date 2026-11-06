"""Only one run at a time on a conversation, across every pod."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.src.security.thread_lease import Claim
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

TTL_SECONDS = 300


@dataclass
class SharedThreadLeases:
    """Thread leases held in Redis, so every replica sees the same one."""

    client: Any = None

    async def _redis(self) -> Any:
        """The Redis client, made on first use."""
        if self.client is not None:
            return self.client
        from agent.aegra.redis import get_async_redis_client

        return await get_async_redis_client()

    @staticmethod
    def _key(thread: str) -> str:
        """The key a thread's lease is held under."""
        return f"thread:lease:{thread}"

    async def claim(self, *, thread: str, subject: str) -> Claim:
        """Take the conversation, or say who already has it."""
        try:
            redis = await self._redis()
            key = self._key(thread)

            if await redis.set(key, subject, nx=True, ex=TTL_SECONDS):
                return Claim(granted=True, held_by=subject)

            holder = await redis.get(key)
            holder = holder.decode() if isinstance(holder, bytes) else holder
            if holder in (None, subject):
                await redis.set(key, subject, ex=TTL_SECONDS)
                return Claim(granted=True, held_by=subject)

            return Claim(granted=False, held_by=holder)
        except Exception as error:
            logger.warning("Could not take the lease on %s: %s", thread, error)
            return Claim(granted=True, held_by=subject)

    async def release(self, *, thread: str, subject: str) -> None:
        """Give it back, if it is yours to give. Never raises."""
        try:
            redis = await self._redis()
            key = self._key(thread)
            holder = await redis.get(key)
            holder = holder.decode() if isinstance(holder, bytes) else holder
            if holder == subject:
                await redis.delete(key)
        except Exception as error:
            logger.warning("Could not release the lease on %s: %s", thread, error)
