"""A turn with nothing in it must not reach the provider."""

from __future__ import annotations

import pytest

from agent.src.infrastructure.middleware import build_nothing_to_send_middleware


class _Message:
    def __init__(self, content):
        self.content = content


class _Request:
    def __init__(self, messages, system_message=""):
        self.messages = messages
        self.system_message = system_message


class _Handler:
    def __init__(self):
        self.called = 0

    async def __call__(self, request):
        self.called += 1
        return "the model answered"


@pytest.fixture
def middleware():
    found = build_nothing_to_send_middleware()
    if found is None:
        pytest.skip("the agent framework is not installed")
    return found


async def _run(middleware, request):
    handler = _Handler()
    found = await middleware.awrap_model_call(request, handler)
    return found, handler


class TestAnEmptyTurn:
    @pytest.mark.asyncio
    async def test_the_provider_is_not_called(self, middleware):
        _found, handler = await _run(middleware, _Request([]))
        assert handler.called == 0

    @pytest.mark.asyncio
    async def test_something_comes_back_rather_than_nothing(self, middleware):
        found, _handler = await _run(middleware, _Request([]))
        assert found is not None

    @pytest.mark.asyncio
    async def test_the_reply_is_about_the_conversation(self, middleware):
        found, _handler = await _run(middleware, _Request([]))
        said = str(found.result[0].content).lower()
        assert "contents" not in said
        assert "message" in said or "nothing" in said

    @pytest.mark.asyncio
    async def test_messages_that_are_all_empty_count_as_empty(self, middleware):
        _found, handler = await _run(
            middleware, _Request([_Message(""), _Message("  ")])
        )
        assert handler.called == 0

    @pytest.mark.asyncio
    async def test_a_system_message_alone_is_still_nothing_to_answer(self, middleware):
        _found, handler = await _run(
            middleware, _Request([], system_message="You are helpful")
        )
        assert handler.called == 0


class TestAnOrdinaryTurn:
    @pytest.mark.asyncio
    async def test_it_goes_through(self, middleware):
        _found, handler = await _run(middleware, _Request([_Message("hello")]))
        assert handler.called == 1

    @pytest.mark.asyncio
    async def test_the_answer_is_not_touched(self, middleware):
        found, _handler = await _run(middleware, _Request([_Message("hello")]))
        assert found == "the model answered"

    @pytest.mark.asyncio
    async def test_content_in_blocks_counts(self, middleware):
        _found, handler = await _run(
            middleware, _Request([_Message([{"type": "text", "text": "hello"}])])
        )
        assert handler.called == 1

    @pytest.mark.asyncio
    async def test_a_tool_result_with_no_text_still_counts(self, middleware):
        class _ToolCall:
            content = ""
            tool_calls = [{"name": "ask", "args": {}}]

        _found, handler = await _run(middleware, _Request([_ToolCall()]))
        assert handler.called == 1


class TestItNeverCostsAGoodTurn:
    @pytest.mark.asyncio
    async def test_a_request_it_cannot_read_goes_through(self, middleware):
        class _Odd:
            pass

        handler = _Handler()
        await middleware.awrap_model_call(_Odd(), handler)
        assert handler.called == 1


class TestItIsActuallyInTheChain:
    """A guard nobody registers guards nothing."""

    @staticmethod
    def _built(enabled):
        from unittest.mock import patch

        from agent.src.infrastructure.middleware import (
            ResolvedMiddlewareConfig,
            build_middleware_list,
        )

        with (
            patch("agent.src.infrastructure.middleware.settings") as mock_settings,
            patch(
                "agent.src.infrastructure.middleware._build_summarization_tool_middleware",
                return_value=None,
            ),
        ):
            mock_settings.MIDDLEWARE_ENABLED = enabled
            return [
                type(found).__name__
                for found in build_middleware_list(ResolvedMiddlewareConfig())
            ]

    def test_it_is_in_the_chain(self):
        assert "NothingToSendMiddleware" in self._built(True)

    def test_it_is_there_with_the_rest_switched_off(self):
        assert "NothingToSendMiddleware" in self._built(False)
