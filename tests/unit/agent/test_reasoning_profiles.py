"""Named ways of answering, and whether offering the choice is honest."""

from __future__ import annotations

import pytest

from agent.src.agent.reasoning_profiles import (
    Profile,
    distinguishable,
    profile_named,
    profiles_from,
    worth_offering,
)


def _config(**over):
    base = {
        "tiers": [
            {"name": "fast", "model": "small"},
            {"name": "balanced", "model": "medium"},
            {"name": "deep", "model": "large"},
        ],
        "profiles": [
            {"name": "fast", "tier": "fast", "effort": "low", "budget_multiplier": 0.5},
            {"name": "balanced", "tier": "balanced", "effort": "medium"},
            {
                "name": "accurate",
                "tier": "deep",
                "effort": "high",
                "budget_multiplier": 2,
            },
        ],
    }
    base.update(over)
    return base


class TestReadingThem:
    def test_each_declared_profile_is_read(self):
        found = profiles_from(_config())
        assert [one.name for one in found] == ["fast", "balanced", "accurate"]

    def test_a_profile_names_a_tier(self):
        assert profile_named(profiles_from(_config()), "accurate").tier == "deep"

    def test_effort_comes_through(self):
        assert profile_named(profiles_from(_config()), "fast").effort == "low"

    def test_the_budget_multiplier_defaults_to_one(self):
        assert (
            profile_named(profiles_from(_config()), "balanced").budget_multiplier == 1.0
        )

    def test_a_configuration_may_define_its_own(self):
        found = profiles_from(
            _config(profiles=[{"name": "overnight", "tier": "deep", "effort": "high"}])
        )
        assert [one.name for one in found] == ["overnight"]

    def test_a_profile_naming_no_tier_is_dropped(self):
        found = profiles_from(
            _config(profiles=[{"name": "ghost", "tier": "nowhere", "effort": "low"}])
        )
        assert found == []

    @pytest.mark.parametrize("broken", [None, "not a mapping", 7, {}])
    def test_a_shape_it_cannot_read_yields_nothing(self, broken):
        assert profiles_from(broken) == []


class TestWhetherTheyDiffer:
    def test_different_models_differ(self):
        assert distinguishable(profiles_from(_config()))

    def test_the_same_model_everywhere_does_not(self):
        same = _config(
            tiers=[
                {"name": "fast", "model": "one"},
                {"name": "balanced", "model": "one"},
                {"name": "deep", "model": "one"},
            ],
            profiles=[
                {"name": "fast", "tier": "fast", "effort": "low"},
                {"name": "balanced", "tier": "balanced", "effort": "low"},
                {"name": "accurate", "tier": "deep", "effort": "low"},
            ],
        )
        assert not distinguishable(profiles_from(same))

    def test_the_same_model_but_different_effort_does_differ(self):
        same_model = _config(
            tiers=[
                {"name": "fast", "model": "one"},
                {"name": "deep", "model": "one"},
            ],
            profiles=[
                {"name": "fast", "tier": "fast", "effort": "low"},
                {"name": "accurate", "tier": "deep", "effort": "high"},
            ],
        )
        assert distinguishable(profiles_from(same_model))

    def test_one_profile_is_not_a_choice(self):
        single = _config(profiles=[{"name": "only", "tier": "fast", "effort": "low"}])
        assert not distinguishable(profiles_from(single))

    def test_none_at_all_is_not_a_choice(self):
        assert not distinguishable([])


class TestWhetherToOfferTheChoice:
    def test_offered_when_the_profiles_differ(self):
        assert worth_offering(_config()) != []

    def test_withheld_when_they_do_not(self):
        same = _config(
            tiers=[{"name": "a", "model": "one"}, {"name": "b", "model": "one"}],
            profiles=[
                {"name": "fast", "tier": "a", "effort": "low"},
                {"name": "accurate", "tier": "b", "effort": "low"},
            ],
        )
        assert worth_offering(same) == []

    def test_withheld_when_nothing_is_declared(self):
        assert worth_offering({"tiers": [{"name": "fast", "model": "one"}]}) == []

    def test_it_never_raises_on_a_broken_configuration(self):
        assert worth_offering("not a mapping") == []
        assert worth_offering(None) == []


class TestWhenRoutingIsOff:
    """A tier nothing routes to cannot make two profiles differ."""

    def _off(self, **over):
        config = _config(**over)
        config["enabled"] = False
        return config

    def test_different_tiers_alone_no_longer_differ(self):
        same_effort = self._off(
            profiles=[
                {"name": "fast", "tier": "fast", "effort": "low"},
                {"name": "accurate", "tier": "deep", "effort": "low"},
            ]
        )
        assert worth_offering(same_effort) == []

    def test_different_effort_still_differs(self):
        assert worth_offering(self._off()) != []

    def test_with_routing_on_the_tier_counts_again(self):
        config = _config(enabled=True)
        config["profiles"] = [
            {"name": "fast", "tier": "fast", "effort": "same"},
            {"name": "accurate", "tier": "deep", "effort": "same"},
        ]
        assert worth_offering(config) != []


class TestTheNamesAreNotEvidence:
    def test_a_profile_does_not_claim_to_be_better(self):
        one = profile_named(profiles_from(_config()), "accurate")
        assert isinstance(one, Profile)
        assert set(vars(one)) == {
            "name",
            "tier",
            "model",
            "effort",
            "budget_multiplier",
        }
