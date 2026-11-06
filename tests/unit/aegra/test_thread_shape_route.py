"""Letting an eval run ask whether a conversation was shortened."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from agent.aegra import eval_routes


def _at(checkpoint: str, count: int) -> dict[str, Any]:
    return {
        "checkpoint_id": checkpoint,
        "values": {"messages": [{"id": f"{checkpoint}-{i}"} for i in range(count)]},
    }


class TestWhatItReports:
    @pytest.mark.asyncio
    async def test_a_shortened_thread_says_so(self):
        history = [_at("c2", 5), _at("c1", 20)]
        with (
            patch.object(
                eval_routes, "_thread_history", AsyncMock(return_value=history)
            ),
            patch.object(eval_routes, "_verify_thread_ownership", AsyncMock()),
        ):
            found = await eval_routes.get_thread_shape("t1", request=None, _token="x")

        assert found["was_shortened"] is True
        assert found["messages_now"] == 5
        assert found["most_messages"] == 20

    @pytest.mark.asyncio
    async def test_a_thread_that_only_grew_does_not(self):
        history = [_at("c2", 20), _at("c1", 4)]
        with (
            patch.object(
                eval_routes, "_thread_history", AsyncMock(return_value=history)
            ),
            patch.object(eval_routes, "_verify_thread_ownership", AsyncMock()),
        ):
            found = await eval_routes.get_thread_shape("t1", request=None, _token="x")

        assert found["was_shortened"] is False
        assert found["messages_now"] == found["most_messages"] == 20

    @pytest.mark.asyncio
    async def test_it_names_the_thread_it_answered_about(self):
        with (
            patch.object(
                eval_routes, "_thread_history", AsyncMock(return_value=[_at("c1", 2)])
            ),
            patch.object(eval_routes, "_verify_thread_ownership", AsyncMock()),
        ):
            found = await eval_routes.get_thread_shape("t1", request=None, _token="x")
        assert found["thread_id"] == "t1"


class TestItIsNotAnOpenDoor:
    @pytest.mark.asyncio
    async def test_a_thread_somebody_does_not_own_is_refused(self):
        from fastapi import HTTPException

        refuse = AsyncMock(side_effect=HTTPException(status_code=403, detail="no"))
        with (
            patch.object(eval_routes, "_verify_thread_ownership", refuse),
            patch.object(eval_routes, "_thread_history", AsyncMock()) as read,
        ):
            with pytest.raises(HTTPException) as raised:
                await eval_routes.get_thread_shape("t1", request=None, _token="x")
        assert raised.value.status_code == 403
        read.assert_not_awaited()

    def test_it_sits_behind_the_developer_gate(self):
        import inspect

        signature = inspect.signature(eval_routes.get_thread_shape)
        default = signature.parameters["_token"].default
        assert getattr(default, "dependency", None) is eval_routes._require_developer


class TestItUsesTheSharedReasoning:
    """Not a fourth answer to "which list is current"."""

    def test_it_reads_the_shared_module(self):
        import inspect

        source = inspect.getsource(eval_routes.get_thread_shape)
        assert "was_shortened" in source
        assert "high_water_mark" in source
