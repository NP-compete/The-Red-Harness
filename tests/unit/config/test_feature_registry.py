"""Ten opt-in capabilities, and one place that decides them."""

from __future__ import annotations

import pytest

from agent.src.agent.config.features import (
    Feature,
    Scope,
    UnknownFeature,
    decide,
)

REGISTRY = {
    "planner_enabled": Feature(scope=Scope.AGENT, default=False, ui_exposed=True),
    "swarm_enabled": Feature(scope=Scope.DEPLOYMENT, default=False, ui_exposed=True),
    "sandbox_backend": Feature(scope=Scope.DEPLOYMENT, default=False, ui_exposed=True),
    "browser_automation_enabled": Feature(
        scope=Scope.DEPLOYMENT,
        default=False,
        ui_exposed=True,
        requires=("sandbox_backend",),
    ),
    "reasoning_profiles_enabled": Feature(
        scope=Scope.USER, default=False, ui_exposed=True
    ),
}


def settled(name, **levels):
    return decide(name, registry=REGISTRY, **levels)


class TestWhatHappensWithNobodySayingAnything:
    def test_a_flag_nobody_set_takes_its_declared_default(self):
        assert settled("planner_enabled").enabled is False

    def test_and_says_the_default_decided_it(self):
        assert settled("planner_enabled").decided_by == "default"

    def test_a_flag_defaulting_on_is_on(self):
        registry = {"x": Feature(scope=Scope.AGENT, default=True)}
        assert decide("x", registry=registry).enabled is True


class TestAFlagNobodyDeclared:
    """Fail closed. An undeclared flag is a typo or a stale reference."""

    def test_it_is_refused_rather_than_guessed(self):
        with pytest.raises(UnknownFeature):
            settled("planner_enbaled")

    def test_the_refusal_names_what_was_asked_for(self):
        with pytest.raises(UnknownFeature, match="planner_enbaled"):
            settled("planner_enbaled")


class TestANarrowerScopeMayNarrow:
    def test_the_user_can_turn_off_what_the_agent_allows(self):
        found = settled("reasoning_profiles_enabled", agent=True, user=False)
        assert found.enabled is False

    def test_and_the_user_is_named_as_having_decided_it(self):
        found = settled("reasoning_profiles_enabled", agent=True, user=False)
        assert found.decided_by == "user"

    def test_the_agent_can_turn_off_what_the_deployment_allows(self):
        found = settled("planner_enabled", deployment=True, agent=False)
        assert found.enabled is False
        assert found.decided_by == "agent"


class TestANarrowerScopeMayNotWiden:
    """The toggle that silently does nothing, made to say so."""

    def test_the_user_cannot_turn_on_what_the_agent_forbids(self):
        found = settled("reasoning_profiles_enabled", agent=False, user=True)
        assert found.enabled is False

    def test_and_the_level_that_actually_decided_is_named(self):
        found = settled("reasoning_profiles_enabled", agent=False, user=True)
        assert found.decided_by == "agent"

    def test_the_agent_cannot_turn_on_what_the_deployment_forbids(self):
        found = settled("planner_enabled", deployment=False, agent=True)
        assert found.enabled is False
        assert found.decided_by == "deployment"

    def test_an_overruled_request_is_reported_as_overruled(self):
        found = settled("planner_enabled", deployment=False, agent=True)
        assert found.overruled is True

    def test_an_honoured_request_is_not(self):
        found = settled("planner_enabled", deployment=True, agent=True)
        assert found.overruled is False


class TestAFlagSetAboveItsOwnScope:
    """Where a flag may be set is declared, and it is enforced."""

    def test_a_deployment_flag_is_not_the_users_to_turn_on(self):
        found = settled("swarm_enabled", deployment=True, user=False)
        assert found.enabled is True

    def test_the_user_setting_it_is_ignored_rather_than_obeyed(self):
        found = settled("swarm_enabled", deployment=False, user=True)
        assert found.enabled is False
        assert found.decided_by == "deployment"


class TestSomethingItDependsOn:
    """`requires` is what stops a half-built path being switched on."""

    def test_it_stays_off_while_its_precondition_is_off(self):
        found = settled("browser_automation_enabled", deployment=True)
        assert found.enabled is False

    def test_the_missing_precondition_is_named(self):
        found = settled("browser_automation_enabled", deployment=True)
        assert found.missing == ("sandbox_backend",)

    def test_it_comes_on_once_the_precondition_is_there(self):
        found = decide(
            "browser_automation_enabled",
            registry=REGISTRY,
            deployment=True,
            others={"sandbox_backend": True},
        )
        assert found.enabled is True

    def test_it_is_reported_even_for_a_flag_nobody_asked_for(self):
        assert settled("browser_automation_enabled").missing == ("sandbox_backend",)

    def test_a_capability_with_no_preconditions_needs_nothing(self):
        assert settled("planner_enabled").missing == ()

    def test_a_precondition_nobody_declared_is_refused(self):
        registry = {
            "x": Feature(scope=Scope.DEPLOYMENT, default=False, requires=("ghost",))
        }
        with pytest.raises(UnknownFeature, match="ghost"):
            decide("x", registry=registry, deployment=True)


class TestWhatTheInterfaceMayShow:
    def test_a_flag_declared_hidden_is_not_offered(self):
        registry = {"x": Feature(scope=Scope.AGENT, default=False, ui_exposed=False)}
        assert decide("x", registry=registry).ui_exposed is False

    def test_a_flag_declared_visible_is(self):
        assert settled("planner_enabled").ui_exposed is True


class TestSettlingTheWholeRegistryAtOnce:
    """A precondition is judged on its settled value, not its default."""

    @staticmethod
    def _all(**levels):
        from agent.src.agent.config.features import effective

        return effective(REGISTRY, **levels)

    def test_every_declared_flag_is_answered(self):
        assert set(self._all()) == set(REGISTRY)

    def test_a_flag_whose_precondition_is_on_comes_on(self):
        found = self._all(
            deployment={"sandbox_backend": True, "browser_automation_enabled": True}
        )
        assert found["browser_automation_enabled"].enabled is True

    def test_a_flag_whose_precondition_is_off_does_not(self):
        found = self._all(deployment={"browser_automation_enabled": True})
        assert found["browser_automation_enabled"].enabled is False

    def test_and_it_says_which_precondition_was_missing(self):
        found = self._all(deployment={"browser_automation_enabled": True})
        assert found["browser_automation_enabled"].missing == ("sandbox_backend",)

    def test_a_precondition_turned_off_takes_its_dependant_with_it(self):
        found = self._all(
            deployment={"sandbox_backend": False, "browser_automation_enabled": True}
        )
        assert found["browser_automation_enabled"].enabled is False


class TestReadingTheDeclaredRegistry:
    @staticmethod
    def _read(raw):
        from agent.src.agent.config.features import from_config

        return from_config(raw)

    def test_a_declaration_becomes_a_feature(self):
        found = self._read({"features": {"x": {"scope": "agent", "default": True}}})
        assert found["x"].default is True

    def test_the_scope_is_carried_across(self):
        found = self._read({"features": {"x": {"scope": "deployment"}}})
        assert found["x"].scope is Scope.DEPLOYMENT

    def test_what_it_costs_is_carried_across(self):
        found = self._read(
            {"features": {"x": {"scope": "agent", "cost": "a model call"}}}
        )
        assert found["x"].cost == "a model call"

    def test_preconditions_are_carried_across(self):
        found = self._read({"features": {"x": {"scope": "agent", "requires": ["y"]}}})
        assert found["x"].requires == ("y",)

    def test_an_unknown_scope_is_refused_rather_than_guessed(self):
        with pytest.raises(ValueError, match="unknown scope"):
            self._read({"features": {"x": {"scope": "universe"}}})

    def test_the_refusal_names_the_flag(self):
        with pytest.raises(ValueError, match="x"):
            self._read({"features": {"x": {"scope": "universe"}}})

    def test_a_declaration_that_is_not_one_is_refused(self):
        with pytest.raises(ValueError, match="not a declaration"):
            self._read({"features": {"x": "on"}})

    def test_a_file_with_no_features_block_declares_nothing(self):
        assert self._read({}) == {}


class TestTheShippedRegistry:
    """The declarations that travel with the deployment."""

    @staticmethod
    def _shipped():
        from pathlib import Path

        import yaml

        from agent.src.agent.config.features import from_config

        path = (
            Path(__file__).parents[3] / "config" / "agent" / "runtime" / "features.yaml"
        )
        return from_config(yaml.safe_load(path.read_text()))

    def test_it_declares_something(self):
        assert self._shipped()

    def test_every_capability_ships_off(self):
        enum = self._shipped()
        assert all(not f.default for f in enum.values() if f.scope != Scope.USER)

    def test_every_precondition_is_itself_declared(self):
        enum = self._shipped()
        for name, feature in enum.items():
            for required in feature.requires:
                assert required in enum, f"{name} requires undeclared {required}"

    def test_everything_offered_in_the_interface_says_what_it_costs(self):
        for name, feature in self._shipped().items():
            if feature.ui_exposed:
                assert feature.cost, f"{name} is offered with no stated cost"

    def test_no_flag_turns_an_authorization_check_off(self):
        names = " ".join(self._shipped())
        assert "authz" not in names and "authorization" not in names
