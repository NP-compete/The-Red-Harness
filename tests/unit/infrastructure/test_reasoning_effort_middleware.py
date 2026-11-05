"""The chosen way of answering reaches the model call."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent.src.infrastructure.middleware import build_reasoning_effort_middleware


class _Model:
    """Enough of a chat model to be rebuilt from."""

    def __init__(self) -> None:
        self.model = "gemini-3.8-flash"
        self.temperature = 0.0


class _Request:
    """Enough of a model request to see what was overridden."""

    def __init__(self) -> None:
        self.overrides: dict[str, Any] = {}
        self.model_settings: dict[str, Any] = {}
        self.model = _Model()

    def override(self, **changes: Any) -> "_Request":
        self.overrides.update(changes)
        return self


def _runtime(profile: str | None):
    runtime = MagicMock()
    runtime.context = {}
    configurable = {"reasoning_profile": profile} if profile is not None else {}
    runtime.config = {"configurable": configurable}
    return runtime


def _call(profile: str | None, *, offered: list[dict] | None = None):
    middleware = build_reasoning_effort_middleware(
        profiles=offered
        if offered is not None
        else [
            {"name": "fast", "effort": "low"},
            {"name": "accurate", "effort": "high"},
        ]
    )
    assert middleware is not None
    request = _Request()
    seen: dict[str, Any] = {}

    def handler(given: Any) -> str:
        seen["request"] = given
        return "answered"

    result = middleware.wrap_model_call(request, handler, _runtime(profile))
    return result, seen["request"]


class TestWhenAProfileWasChosen:
    """It swaps the model, because the budget is built into one."""

    def test_a_careful_profile_builds_a_model_with_the_budget(self):
        _, request = _call("accurate")
        assert request.overrides["model"].thinking_budget == 4096

    def test_a_quick_profile_builds_one_with_reasoning_off(self):
        _, request = _call("fast")
        assert request.overrides["model"].thinking_budget == 0

    def test_it_does_not_set_a_per_call_setting_nothing_reads(self):
        _, request = _call("accurate")
        assert "model_settings" not in request.overrides

    def test_the_answer_still_comes_back(self):
        answer, _ = _call("accurate")
        assert answer == "answered"


class TestWhenNothingWasChosen:
    def test_no_override_at_all(self):
        _, request = _call(None)
        assert request.overrides == {}

    def test_an_empty_choice_is_no_choice(self):
        _, request = _call("")
        assert request.overrides == {}

    def test_a_profile_the_deployment_does_not_offer_is_ignored(self):
        _, request = _call("accurate", offered=[{"name": "fast", "effort": "low"}])
        assert request.overrides == {}

    def test_an_effort_with_no_budget_is_ignored(self):
        _, request = _call("odd", offered=[{"name": "odd", "effort": "enthusiastic"}])
        assert request.overrides == {}


class TestItNeverBreaksTheRun:
    @pytest.mark.parametrize("broken", [None, "nonsense", 7, {}])
    def test_a_runtime_it_cannot_read_still_answers(self, broken):
        middleware = build_reasoning_effort_middleware(
            profiles=[{"name": "fast", "effort": "low"}]
        )
        request = _Request()
        answer = middleware.wrap_model_call(request, lambda given: "answered", broken)
        assert answer == "answered"
        assert request.overrides == {}

    def test_no_profiles_means_the_middleware_is_not_built(self):
        assert build_reasoning_effort_middleware(profiles=[]) is None


class TestTheAsyncPathAgrees:
    @pytest.mark.asyncio
    async def test_it_applies_the_same_budget(self):
        middleware = build_reasoning_effort_middleware(
            profiles=[{"name": "accurate", "effort": "high"}]
        )
        request = _Request()

        async def handler(given: Any) -> str:
            return "answered"

        answer = await middleware.awrap_model_call(
            request, handler, _runtime("accurate")
        )
        assert answer == "answered"
        assert request.overrides["model"].thinking_budget == 4096


class TestThroughTheRealBuilder:
    """The middleware, the real configuration, the real model builder."""

    def _built_for(self, profile_name: str):
        import yaml

        from agent.src.agent.reasoning_profiles import worth_offering
        from agent.src.infrastructure.middleware import (
            build_reasoning_effort_middleware,
        )

        with open("config/agent/runtime/router.yaml") as handle:
            offered = worth_offering(yaml.safe_load(handle))
        assert offered, "the shipped configuration offers no profiles"

        middleware = build_reasoning_effort_middleware(
            [{"name": one.name, "effort": one.effort} for one in offered]
        )
        assert middleware is not None

        request = _Request()
        with patch(
            "agent.src.agent.llm.get_service_account_credentials",
            return_value=(MagicMock(), "a-project"),
        ):
            middleware.wrap_model_call(
                request, lambda given: "answered", _runtime(profile_name)
            )
        return request

    def test_the_quick_profile_reaches_a_model_with_reasoning_off(self):
        built = self._built_for("fast")
        assert built.overrides["model"].thinking_budget == 0

    def test_the_careful_profile_reaches_a_model_that_may_think(self):
        built = self._built_for("accurate")
        assert built.overrides["model"].thinking_budget == 4096

    def test_the_two_are_not_the_same_request(self):
        quick = self._built_for("fast").overrides["model"].thinking_budget
        careful = self._built_for("accurate").overrides["model"].thinking_budget
        assert quick != careful
