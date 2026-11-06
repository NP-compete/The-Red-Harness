"""Where a deployment's answer about a capability is kept."""

from __future__ import annotations

from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

KEY = "features:overrides"


def user_key(user_id: str) -> str:
    """Where this person's answers are kept."""
    return f"features:user:{user_id}"


async def _async_client() -> Any:
    """An async Redis client."""
    from agent.aegra.redis import get_async_redis_client

    return await get_async_redis_client()


class FeatureOverrides:
    """The overrides, as the endpoint sees them."""

    def __init__(self, client_factory: Any = None) -> None:
        """Build overrides backed by `client_factory`, or Redis by default."""
        self._factory = client_factory or _async_client

    async def _client(self) -> Any:
        """The client, awaiting the factory if it is async."""
        found = self._factory()
        if hasattr(found, "__await__"):
            return await found
        return found

    async def available(self) -> bool:
        """Whether a change made now would still be here later."""
        try:
            return await self._client() is not None
        except Exception:
            logger.warning("No override store available", exc_info=True)
            return False

    async def read(self) -> dict[str, bool]:
        """Every override currently set, or nothing if the store is unreachable."""
        try:
            client = await self._client()
            if client is None:
                return {}
            raw = await client.hgetall(KEY)
        except Exception:
            logger.warning("Could not read feature overrides", exc_info=True)
            return {}
        return {_text(name): _text(value) == "1" for name, value in (raw or {}).items()}

    async def read_for(self, user_id: str) -> dict[str, bool]:
        """What this person has decided, for the flags they may."""
        if not user_id:
            return {}
        try:
            client = await self._client()
            if client is None:
                return {}
            raw = await client.hgetall(user_key(user_id))
        except Exception:
            logger.warning("Could not read a person's overrides", exc_info=True)
            return {}
        return {_text(name): _text(value) == "1" for name, value in (raw or {}).items()}

    async def write_for(self, user_id: str, key: str, enabled: bool) -> None:
        """Set `key` for one user."""
        if not user_id:
            raise RuntimeError("no user to write an override for")
        client = await self._client()
        if client is None:
            raise RuntimeError("no override store")
        await client.hset(user_key(user_id), key, "1" if enabled else "0")
        logger.info(
            "Capability %s set to %s for one person", key, "on" if enabled else "off"
        )

    async def write(self, key: str, enabled: bool) -> None:
        """Set `key` for everyone."""
        client = await self._client()
        if client is None:
            raise RuntimeError("no override store")
        await client.hset(KEY, key, "1" if enabled else "0")
        logger.info("Capability %s set to %s", key, "on" if enabled else "off")


def _text(value: Any) -> str:
    """`value` as a string, decoding bytes."""
    return value.decode() if isinstance(value, bytes) else str(value)


def overrides() -> FeatureOverrides:
    """The store, which resolves its client when it is used."""
    return FeatureOverrides()
