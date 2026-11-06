"""A capability that is off leaves nothing behind."""

from __future__ import annotations

import pathlib

import pytest
import yaml

from agent.src.agent.config.features import Scope, effective, from_config

REGISTRY = (
    pathlib.Path(__file__).resolve().parents[3]
    / "config"
    / "agent"
    / "runtime"
    / "features.yaml"
)


def _registry():
    raw = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    return from_config(raw)


def _names():
    return sorted(_registry())


class TestTheSweepIsWorthRunning:
    def test_the_registry_is_there_and_populated(self):
        assert len(_registry()) >= 5

    def test_every_flag_declares_a_scope(self):
        for name, feature in _registry().items():
            assert isinstance(feature.scope, Scope), f"{name} has no usable scope"


class TestOffIsTheSameAsAbsent:
    """The invariant, one flag at a time."""

    @pytest.mark.parametrize("name", _names())
    def test_setting_it_off_changes_nothing(self, name: str):
        registry = _registry()
        scope = registry[name].scope.value

        absent = effective(registry)
        explicit = effective(registry, **{scope: {name: False}})

        for other in registry:
            assert explicit[other].enabled == absent[other].enabled, (
                f"setting {name} off changed whether {other} is on"
            )

    @pytest.mark.parametrize("name", _names())
    def test_it_is_off_to_begin_with(self, name: str):
        settled = effective(_registry())[name]
        feature = _registry()[name]
        if isinstance(feature.default, bool) and feature.default is False:
            assert not settled.enabled, f"{name} defaults off but settles on"


class TestAFlagCanActuallyBeTurnedOn:
    """Otherwise it is a switch wired to nothing."""

    @pytest.mark.parametrize("name", _names())
    def test_asking_for_it_either_turns_it_on_or_says_why_not(self, name: str):
        registry = _registry()
        feature = registry[name]
        if not isinstance(feature.default, bool):
            pytest.skip(f"{name} is not a boolean")

        scope = feature.scope.value
        settled = effective(registry, **{scope: {name: True}})[name]

        if settled.enabled:
            return
        assert settled.missing or settled.overruled, (
            f"{name} cannot be turned on and gives no reason: a switch "
            f"wired to nothing looks exactly like this."
        )


class TestWhatDecidedItIsReported:
    @pytest.mark.parametrize("name", _names())
    def test_an_untouched_flag_says_the_default_decided_it(self, name: str):
        settled = effective(_registry())[name]
        assert settled.decided_by in {"default", "unavailable"}, (
            f"{name} with nothing set claims it was decided by {settled.decided_by}"
        )


class TestTheCheckCanFail:
    def test_a_flag_that_defaults_on_is_caught(self):
        registry = from_config(
            {"features": {"loud": {"scope": "agent", "default": True}}}
        )
        assert effective(registry)["loud"].enabled

    def test_turning_one_off_can_move_another(self):
        registry = from_config(
            {
                "features": {
                    "base": {"scope": "agent", "default": True},
                    "built_on_it": {
                        "scope": "agent",
                        "default": True,
                        "requires": ["base"],
                    },
                }
            }
        )
        assert effective(registry)["built_on_it"].enabled
        assert not effective(registry, agent={"base": False})["built_on_it"].enabled
