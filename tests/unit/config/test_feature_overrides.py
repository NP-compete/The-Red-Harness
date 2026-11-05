"""Where a deployment's answer about a capability is kept."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.src.agent.config.feature_overrides import KEY, FeatureOverrides


class _AsyncClient:
    def __init__(self, held=None):
        self.held = held or {}
        self.wrote: list[tuple[str, str, str]] = []

    async def hgetall(self, key):
        return dict(self.held)

    async def hset(self, key, field, value):
        self.wrote.append((key, field, value))


def _store(client):
    return FeatureOverrides(lambda: client)


class TestItUsesTheClientTheProcessActuallyHas:
    """An async client, reached through the async accessor."""

    @pytest.mark.asyncio
    async def test_the_store_asks_for_the_async_client(self):
        from agent.src.agent.config import feature_overrides

        got = AsyncMock(return_value=_AsyncClient())
        with patch.object(feature_overrides, "_async_client", got):
            await feature_overrides.overrides().read()
        assert got.await_count == 1

    @pytest.mark.asyncio
    async def test_reading_awaits_the_client(self):
        found = await _store(_AsyncClient({"swarm_enabled": "1"})).read()
        assert found == {"swarm_enabled": True}

    @pytest.mark.asyncio
    async def test_writing_awaits_the_client(self):
        client = _AsyncClient()
        await _store(client).write("swarm_enabled", True)
        assert client.wrote == [(KEY, "swarm_enabled", "1")]


class TestWhatIsStored:
    @pytest.mark.asyncio
    async def test_off_is_stored_rather_than_removed(self):
        client = _AsyncClient()
        await _store(client).write("swarm_enabled", False)
        assert client.wrote == [(KEY, "swarm_enabled", "0")]

    @pytest.mark.asyncio
    async def test_bytes_from_the_client_are_read_as_text(self):
        found = await _store(_AsyncClient({b"swarm_enabled": b"1"})).read()
        assert found == {"swarm_enabled": True}

    @pytest.mark.asyncio
    async def test_a_zero_reads_as_off(self):
        found = await _store(_AsyncClient({"swarm_enabled": "0"})).read()
        assert found == {"swarm_enabled": False}


class TestWhenThereIsNoStore:
    @pytest.mark.asyncio
    async def test_it_says_so_rather_than_pretending(self):
        assert await _store(None).available() is False

    @pytest.mark.asyncio
    async def test_reading_falls_back_to_the_declared_defaults(self):
        assert await _store(None).read() == {}

    @pytest.mark.asyncio
    async def test_writing_refuses(self):
        with pytest.raises(RuntimeError):
            await _store(None).write("swarm_enabled", True)

    @pytest.mark.asyncio
    async def test_a_store_that_is_there_says_so(self):
        assert await _store(_AsyncClient()).available() is True


class TestAStoreThatFailsMidRead:
    @pytest.mark.asyncio
    async def test_the_defaults_are_reported_rather_than_off(self):
        class _Broken:
            async def hgetall(self, key):
                raise ConnectionError("gone")

        assert await _store(_Broken()).read() == {}
