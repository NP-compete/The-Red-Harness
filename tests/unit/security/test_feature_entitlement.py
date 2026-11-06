"""Which features an organisation may use."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.feature_entitlement import (
    Entitlement,
    Reason,
    may_use_feature,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

PLANS = {
    "starter": ("chat",),
    "business": ("chat", "unattended-runs", "external-sharing"),
}


def entitlement(**kwargs) -> Entitlement:
    defaults = {
        "plan": "business",
        "plan_features": PLANS,
        "enabled": ("chat", "unattended-runs", "external-sharing"),
        "trials": {},
        "suspended": False,
    }
    defaults.update(kwargs)
    return Entitlement(**defaults)


def test_a_feature_in_the_plan_may_be_used():
    assert may_use_feature("unattended-runs", entitlement(), now=NOW).permitted is True


def test_a_feature_outside_the_plan_may_not_be_used():
    starter = entitlement(plan="starter", enabled=("chat",))
    assert (
        may_use_feature("unattended-runs", starter, now=NOW).reason
        is Reason.NOT_IN_PLAN
    )


def test_a_feature_the_plan_allows_but_nobody_turned_on_is_refused():
    off = entitlement(enabled=("chat",))
    assert may_use_feature("unattended-runs", off, now=NOW).reason is Reason.TURNED_OFF


def test_a_feature_turned_off_can_be_turned_on_by_the_organisation():
    off = entitlement(enabled=("chat",))
    assert may_use_feature("unattended-runs", off, now=NOW).self_serve is True


def test_a_feature_outside_the_plan_cannot_be_turned_on_by_the_organisation():
    starter = entitlement(plan="starter", enabled=("chat",))
    assert may_use_feature("unattended-runs", starter, now=NOW).self_serve is False


def test_a_trial_opens_a_feature_outside_the_plan():
    trial = entitlement(
        plan="starter",
        enabled=("chat", "external-sharing"),
        trials={"external-sharing": NOW + timedelta(days=7)},
    )
    assert may_use_feature("external-sharing", trial, now=NOW).permitted is True


def test_a_trial_says_it_is_a_trial():
    trial = entitlement(
        plan="starter",
        enabled=("chat", "external-sharing"),
        trials={"external-sharing": NOW + timedelta(days=7)},
    )
    assert may_use_feature("external-sharing", trial, now=NOW).on_trial is True


def test_a_trial_says_when_it_ends():
    ends = NOW + timedelta(days=7)
    trial = entitlement(
        plan="starter",
        enabled=("chat", "external-sharing"),
        trials={"external-sharing": ends},
    )
    assert may_use_feature("external-sharing", trial, now=NOW).trial_ends == ends


def test_an_expired_trial_closes_the_feature_again():
    expired = entitlement(
        plan="starter",
        enabled=("chat", "external-sharing"),
        trials={"external-sharing": NOW - timedelta(days=1)},
    )
    assert may_use_feature("external-sharing", expired, now=NOW).permitted is False


def test_an_expired_trial_says_the_trial_ended():
    expired = entitlement(
        plan="starter",
        enabled=("chat", "external-sharing"),
        trials={"external-sharing": NOW - timedelta(days=1)},
    )
    assert (
        may_use_feature("external-sharing", expired, now=NOW).reason
        is Reason.TRIAL_ENDED
    )


def test_a_trial_does_not_need_turning_on_separately():
    trial = entitlement(
        plan="starter",
        enabled=("chat",),
        trials={"external-sharing": NOW + timedelta(days=7)},
    )
    assert may_use_feature("external-sharing", trial, now=NOW).permitted is True


def test_a_suspended_organisation_may_use_nothing():
    assert (
        may_use_feature("chat", entitlement(suspended=True), now=NOW).reason
        is Reason.SUSPENDED
    )


def test_suspension_outranks_a_trial():
    trial = entitlement(
        suspended=True, trials={"external-sharing": NOW + timedelta(days=7)}
    )
    assert may_use_feature("external-sharing", trial, now=NOW).permitted is False


def test_a_feature_nobody_has_heard_of_is_refused():
    assert (
        may_use_feature("teleportation", entitlement(), now=NOW).reason
        is Reason.UNKNOWN
    )


def test_an_unknown_plan_is_refused():
    with pytest.raises(ValueError):
        entitlement(plan="imaginary")


def test_a_permitted_feature_has_no_reason_to_give():
    assert may_use_feature("chat", entitlement(), now=NOW).reason is None


def test_a_feature_without_a_name_is_refused():
    with pytest.raises(ValueError):
        may_use_feature("  ", entitlement(), now=NOW)
