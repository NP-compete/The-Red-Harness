"""Model-routing middleware."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from agent.src.routing.classifier import RoutingDecision
from agent.src.routing.config import ModelTier, RouterConfig
from agent.src.routing.middleware import (
    STATE_KEY,
    _first_human_text,
    _latest_human_text,
    build_model_router_middleware,
)

CHEAP = ModelTier(name="cheap", model="gemini-flash", criteria="simple")
STRONG = ModelTier(name="strong", model="gemini-pro", criteria="hard")


def _config(**kwargs) -> RouterConfig:
    return RouterConfig(**{"enabled": True, "tiers": [CHEAP, STRONG], **kwargs})


class TestHumanText:
    def test_reads_a_dict_message(self):
        assert _first_human_text([{"type": "human", "content": "hello"}]) == "hello"

    def test_reads_an_object_message(self):
        message = SimpleNamespace(type="human", content="hello", role=None)
        assert _first_human_text([message]) == "hello"

    def test_accepts_role_instead_of_type(self):
        assert _first_human_text([{"role": "user", "content": "hi"}]) == "hi"

    def test_joins_structured_content_blocks(self):
        message = {
            "type": "human",
            "content": [{"text": "part one"}, {"text": "part two"}, {"image": "x"}],
        }
        assert _first_human_text([message]) == "part one part two "

    def test_skips_non_human_turns(self):
        messages = [
            {"type": "ai", "content": "answer"},
            {"type": "human", "content": "q"},
        ]
        assert _first_human_text(messages) == "q"

    def test_empty_when_nobody_has_spoken(self):
        assert _first_human_text([{"type": "ai", "content": "hi"}]) == ""

    def test_latest_takes_the_most_recent_turn(self):
        messages = [
            {"type": "human", "content": "first"},
            {"type": "human", "content": "second"},
        ]
        assert _latest_human_text(messages) == "second"


class TestBuildModelRouterMiddleware:
    def test_none_when_routing_is_off(self):
        assert build_model_router_middleware(_config(enabled=False)) is None

    def test_enabled_with_one_tier_is_rejected_at_config_time(self):
        with pytest.raises(ValidationError):
            RouterConfig(enabled=True, tiers=[CHEAP])

    def test_none_when_a_single_tier_reaches_the_builder_anyway(self):
        built = RouterConfig(enabled=False, tiers=[CHEAP])
        object.__setattr__(built, "enabled", True)
        assert build_model_router_middleware(built) is None

    def test_built_when_configured(self):
        with patch("agent.src.agent.llm.create_model", return_value=MagicMock()):
            assert build_model_router_middleware(_config()) is not None


async def _run_route(cfg: RouterConfig, request, decision: RoutingDecision, model=None):
    """Build the middleware and invoke the wrapped routing function."""
    captured = {}

    def _wrap(fn, name=None):
        captured["fn"] = fn
        return MagicMock()

    with (
        patch("langchain.agents.middleware.wrap_model_call", _wrap),
        patch(
            "agent.src.agent.llm.create_model",
            MagicMock(return_value=model if model is not None else MagicMock()),
        ),
        patch(
            "agent.src.routing.middleware.choose_tier",
            new=AsyncMock(return_value=decision),
        ),
    ):
        build_model_router_middleware(cfg)
        handler = AsyncMock(return_value="answered")
        result = await captured["fn"](request, handler)
    return result, handler


def _request(messages, state=None):
    request = MagicMock()
    request.messages = messages
    request.state = state if state is not None else {}
    request.override = MagicMock(return_value="routed-request")
    return request


class TestRoute:
    @pytest.mark.asyncio
    async def test_routes_to_the_chosen_tier(self):
        request = _request([{"type": "human", "content": "something hard"}])
        decision = RoutingDecision(
            tier=STRONG, reason="looks hard", method="classifier"
        )
        result, handler = await _run_route(_config(), request, decision)

        assert result == "answered"
        request.override.assert_called_once()
        handler.assert_awaited_once_with("routed-request")

    @pytest.mark.asyncio
    async def test_first_message_strategy_sticks_to_the_earlier_choice(self):
        request = _request(
            [{"type": "human", "content": "anything"}], state={STATE_KEY: "cheap"}
        )
        decision = RoutingDecision(tier=STRONG, reason="unused", method="classifier")
        with patch(
            "agent.src.routing.middleware.choose_tier",
            new=AsyncMock(side_effect=AssertionError("should not re-route")),
        ):
            await _run_route(_config(), request, decision)

    @pytest.mark.asyncio
    async def test_every_turn_strategy_re_routes_despite_a_remembered_tier(self):
        request = _request(
            [{"type": "human", "content": "now something hard"}],
            state={STATE_KEY: "cheap"},
        )
        decision = RoutingDecision(tier=STRONG, reason="escalated", method="classifier")
        await _run_route(_config(strategy="every_turn"), request, decision)
        request.override.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_the_default_model_when_a_tier_cannot_be_built(self):
        request = _request([{"type": "human", "content": "hi"}])
        decision = RoutingDecision(tier=STRONG, reason="hard", method="classifier")

        captured = {}

        def _wrap(fn, name=None):
            captured["fn"] = fn
            return MagicMock()

        with (
            patch("langchain.agents.middleware.wrap_model_call", _wrap),
            patch(
                "agent.src.agent.llm.create_model",
                MagicMock(side_effect=RuntimeError("no credentials")),
            ),
            patch(
                "agent.src.routing.middleware.choose_tier",
                new=AsyncMock(return_value=decision),
            ),
        ):
            build_model_router_middleware(_config())
            handler = AsyncMock(return_value="answered anyway")
            result = await captured["fn"](request, handler)

        assert result == "answered anyway"
        request.override.assert_not_called()
        handler.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_unknown_tier_name_also_falls_back(self):
        request = _request([{"type": "human", "content": "hi"}])
        ghost = ModelTier(name="ghost", model="nope", criteria="x")
        decision = RoutingDecision(tier=ghost, reason="?", method="classifier")
        result, handler = await _run_route(_config(), request, decision)

        assert result == "answered"
        handler.assert_awaited_once_with(request)


class TestRoutingIsRecorded:
    """Routing must be visible after the fact."""

    @pytest.mark.asyncio
    async def test_records_the_tier_and_how_it_was_chosen(self):
        from types import SimpleNamespace

        answered = SimpleNamespace(additional_kwargs={}, content="hi")
        request = _request([{"type": "human", "content": "something hard"}])
        decision = RoutingDecision(
            tier=STRONG, reason="looks hard", method="classifier"
        )

        captured = {}

        def _wrap(fn, name=None):
            captured["fn"] = fn
            return MagicMock()

        with (
            patch("langchain.agents.middleware.wrap_model_call", _wrap),
            patch(
                "agent.src.agent.llm.create_model",
                MagicMock(return_value=MagicMock()),
            ),
            patch(
                "agent.src.routing.middleware.choose_tier",
                new=AsyncMock(return_value=decision),
            ),
        ):
            build_model_router_middleware(_config())
            await captured["fn"](request, AsyncMock(return_value=answered))

        assert answered.additional_kwargs["routed_tier"] == "strong"
        assert answered.additional_kwargs["routed_by"] == "classifier"

    @pytest.mark.asyncio
    async def test_an_unannotatable_response_does_not_fail_the_turn(self):
        request = _request([{"type": "human", "content": "hi"}])
        decision = RoutingDecision(tier=STRONG, reason="hard", method="rule")
        result, _ = await _run_route(_config(), request, decision)
        assert result == "answered"
