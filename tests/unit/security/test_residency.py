"""Keeping a run's data in the places it is allowed to be."""

from __future__ import annotations

import pytest

from agent.src.security.residency import (
    Placement,
    Policy,
    Refusal,
    place_run,
)

POLICY = Policy(
    allowed_regions=("eu-west", "eu-central"),
    preferred_region="eu-west",
    allow_transit_through=("eu-north",),
)


def test_a_run_lands_in_the_preferred_region():
    assert place_run(POLICY, available=("eu-west", "eu-central")).region == "eu-west"


def test_a_run_lands_somewhere_allowed_when_the_preferred_region_is_down():
    assert place_run(POLICY, available=("eu-central",)).region == "eu-central"


def test_a_run_with_nowhere_allowed_is_refused():
    placement = place_run(POLICY, available=("us-east",))
    assert placement.refusal is Refusal.NO_ALLOWED_REGION


def test_a_refused_run_is_not_placed_somewhere_convenient():
    assert place_run(POLICY, available=("us-east",)).region == ""


def test_a_refusal_names_the_regions_that_would_have_been_allowed():
    reason = place_run(POLICY, available=("us-east",)).reason
    assert "eu-west" in reason


def test_a_run_with_no_regions_at_all_is_refused():
    assert place_run(POLICY, available=()).refusal is Refusal.NO_ALLOWED_REGION


def test_a_transit_region_is_not_somewhere_to_run():
    assert (
        place_run(POLICY, available=("eu-north",)).refusal is Refusal.NO_ALLOWED_REGION
    )


def test_a_transit_region_may_carry_the_traffic():
    placement = place_run(POLICY, available=("eu-west",))
    assert placement.may_transit("eu-north") is True


def test_an_allowed_region_may_also_carry_the_traffic():
    placement = place_run(POLICY, available=("eu-west",))
    assert placement.may_transit("eu-central") is True


def test_an_unlisted_region_may_not_carry_the_traffic():
    placement = place_run(POLICY, available=("eu-west",))
    assert placement.may_transit("us-east") is False


def test_a_refused_placement_may_carry_nothing():
    placement = place_run(POLICY, available=("us-east",))
    assert placement.may_transit("eu-north") is False


def test_the_placement_says_it_was_not_the_preferred_region():
    placement = place_run(POLICY, available=("eu-central",))
    assert placement.degraded is True


def test_the_preferred_region_is_not_degraded():
    assert place_run(POLICY, available=("eu-west",)).degraded is False


def test_a_policy_whose_preference_is_not_allowed_is_refused():
    with pytest.raises(ValueError):
        Policy(
            allowed_regions=("eu-west",),
            preferred_region="us-east",
            allow_transit_through=(),
        )


def test_a_policy_with_no_allowed_regions_is_refused():
    with pytest.raises(ValueError):
        Policy(allowed_regions=(), preferred_region="", allow_transit_through=())


def test_a_policy_that_allows_transit_through_a_processing_region_is_fine():
    policy = Policy(
        allowed_regions=("eu-west",),
        preferred_region="eu-west",
        allow_transit_through=("eu-west",),
    )
    assert place_run(policy, available=("eu-west",)).region == "eu-west"


def test_the_placement_is_stable_for_the_same_inputs():
    first = place_run(POLICY, available=("eu-central", "eu-west"))
    second = place_run(POLICY, available=("eu-central", "eu-west"))
    assert first.region == second.region


def test_an_isinstance_check_is_enough_to_know_a_placement_was_made():
    assert isinstance(place_run(POLICY, available=("eu-west",)), Placement)
