"""What a person takes with them, and what leaving removes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.aegra import my_data_routes


def _repository(memories=(), rules=()):
    fake = AsyncMock()
    fake.list_memories.return_value = list(memories)
    fake.list_rules.return_value = list(rules)
    fake.delete_memory.return_value = True
    return fake


class _Memory:
    def __init__(self, text: str, memory_id: str = "m1") -> None:
        self.id = memory_id
        self.content = text
        self.created_at = None
        self.thread_id = "thread-1"


class TestTheExportIncludesMemories:
    @pytest.mark.asyncio
    async def test_a_saved_memory_appears(self):
        repo = _repository(memories=[_Memory("prefers metric units")])
        with patch.object(my_data_routes, "_memory_repository", return_value=repo):
            held = await my_data_routes._collect_async("someone")
        assert "memories" in held
        assert any("metric" in str(entry) for entry in held["memories"])

    @pytest.mark.asyncio
    async def test_the_conversation_it_came_from_travels_with_it(self):
        repo = _repository(memories=[_Memory("prefers metric units")])
        with patch.object(my_data_routes, "_memory_repository", return_value=repo):
            held = await my_data_routes._collect_async("someone")
        assert held["memories"][0].get("thread_id") == "thread-1"

    @pytest.mark.asyncio
    async def test_a_store_that_is_down_does_not_empty_the_export(self):
        repo = AsyncMock()
        repo.list_memories.side_effect = RuntimeError("database is away")
        repo.list_rules.return_value = []
        with patch.object(my_data_routes, "_memory_repository", return_value=repo):
            held = await my_data_routes._collect_async("someone")
        assert "documents" in held or "artifacts" in held


class TestDeletingRemovesThem:
    @pytest.mark.asyncio
    async def test_a_memory_is_deleted(self):
        repo = _repository(memories=[_Memory("prefers metric units")])
        with patch.object(my_data_routes, "_memory_repository", return_value=repo):
            await my_data_routes._remove_async("someone", "memories", ["m1"])
        repo.delete_memory.assert_awaited()

    @pytest.mark.asyncio
    async def test_deleting_somebody_elses_memory_is_not_possible(self):
        repo = _repository(memories=[_Memory("x")])
        with patch.object(my_data_routes, "_memory_repository", return_value=repo):
            await my_data_routes._remove_async("someone", "memories", ["m1"])
        call = repo.delete_memory.await_args
        assert "someone" in call.args or "someone" in call.kwargs.values()


class TestThePreviewSaysSo:
    @pytest.mark.asyncio
    async def test_memories_are_counted_before_anything_is_deleted(self):
        repo = _repository(memories=[_Memory("a"), _Memory("b", "m2")])
        with patch.object(my_data_routes, "_memory_repository", return_value=repo):
            held = await my_data_routes._collect_async("someone")
        assert len(held["memories"]) == 2
