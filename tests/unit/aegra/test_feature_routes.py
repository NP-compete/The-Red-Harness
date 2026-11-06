"""What the interface is allowed to know about the flags."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.src.agent.config.features import Feature, Scope

REGISTRY = {
    "planner_enabled": Feature(
        scope=Scope.AGENT, default=False, ui_exposed=True, cost="a model call"
    ),
    "sandbox_backend": Feature(scope=Scope.DEPLOYMENT, default=False, ui_exposed=True),
    "browser_automation_enabled": Feature(
        scope=Scope.DEPLOYMENT,
        default=False,
        ui_exposed=True,
        requires=("sandbox_backend",),
        cost="renders pages the agent did not write",
    ),
    "internal_only": Feature(scope=Scope.DEPLOYMENT, default=True, ui_exposed=False),
}


def _reported(**levels):
    from agent.aegra.feature_routes import describe_features

    with patch("agent.aegra.feature_routes._registry", return_value=REGISTRY):
        return describe_features(**levels)


def _by_key(reported):
    return {f["key"]: f for f in reported["features"]}


class TestWhatIsReported:
    def test_a_declared_capability_appears(self):
        assert "planner_enabled" in _by_key(_reported())

    def test_it_says_whether_it_is_on(self):
        assert _by_key(_reported())["planner_enabled"]["enabled"] is False

    def test_it_says_which_level_decided(self):
        assert _by_key(_reported())["planner_enabled"]["decided_by"] == "default"

    def test_it_says_where_the_flag_may_be_set(self):
        assert _by_key(_reported())["planner_enabled"]["scope"] == "agent"

    def test_it_says_what_turning_it_on_costs(self):
        assert _by_key(_reported())["planner_enabled"]["cost"] == "a model call"


class TestWhatIsNotReported:
    def test_a_capability_declared_hidden_is_not_offered(self):
        assert "internal_only" not in _by_key(_reported())


class TestAnUnmetPrecondition:
    """The reason a switch will not do anything, said out loud."""

    def test_the_capability_is_reported_off(self):
        found = _by_key(_reported(deployment={"browser_automation_enabled": True}))
        assert found["browser_automation_enabled"]["enabled"] is False

    def test_what_is_missing_is_named(self):
        found = _by_key(_reported(deployment={"browser_automation_enabled": True}))
        assert found["browser_automation_enabled"]["missing"] == ["sandbox_backend"]

    def test_it_is_named_before_anybody_asks(self):
        found = _by_key(_reported())["browser_automation_enabled"]
        assert found["missing"] == ["sandbox_backend"]

    def test_a_capability_with_no_preconditions_names_none(self):
        assert _by_key(_reported())["planner_enabled"]["missing"] == []


class TestARequestAWiderScopeRefused:
    def test_it_is_reported_as_overruled(self):
        found = _by_key(
            _reported(
                deployment={"planner_enabled": False},
                agent={"planner_enabled": True},
            )
        )
        assert found["planner_enabled"]["overruled"] is True

    def test_and_the_level_that_refused_is_named(self):
        found = _by_key(
            _reported(
                deployment={"planner_enabled": False},
                agent={"planner_enabled": True},
            )
        )
        assert found["planner_enabled"]["decided_by"] == "deployment"


class TestTheEndpointItself:
    @pytest.mark.asyncio
    async def test_it_answers_with_the_registry(self):
        from agent.aegra.feature_routes import features

        with patch("agent.aegra.feature_routes._registry", return_value=REGISTRY):
            answered = await features(MagicMock())
        assert any(f["key"] == "planner_enabled" for f in answered["features"])

    @pytest.mark.asyncio
    async def test_a_registry_it_cannot_read_reports_nothing_rather_than_failing(self):
        from agent.aegra.feature_routes import features

        with patch(
            "agent.aegra.feature_routes._registry",
            side_effect=ValueError("unknown scope"),
        ):
            answered = await features(MagicMock())
        assert answered["features"] == []

    @pytest.mark.asyncio
    async def test_and_says_it_could_not_read_them(self):
        from agent.aegra.feature_routes import features

        with patch(
            "agent.aegra.feature_routes._registry",
            side_effect=ValueError("unknown scope"),
        ):
            answered = await features(MagicMock())
        assert answered["unreadable"] is True
