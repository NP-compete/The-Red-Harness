"""Turning the groups an identity provider reports into teams and roles."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.group_sync import Mapping, Snapshot, reconcile

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

MAPPING = Mapping(
    teams_by_group={"eng-all": "engineering", "fin-all": "finance"},
    roles_by_group={"platform-admins": "platform-admin", "fin-approvers": "approver"},
)


def snapshot(**kwargs) -> Snapshot:
    defaults = {
        "person": "ana",
        "groups": ("eng-all",),
        "taken_at": NOW,
        "current_teams": ("engineering",),
        "current_roles": (),
    }
    defaults.update(kwargs)
    return Snapshot(**defaults)


def test_nothing_changes_when_the_groups_match():
    assert reconcile(snapshot(), MAPPING, now=NOW).changed is False


def test_a_new_group_adds_a_team():
    joined = snapshot(groups=("eng-all", "fin-all"))
    assert "finance" in reconcile(joined, MAPPING, now=NOW).teams


def test_a_removed_group_removes_a_team():
    left = snapshot(groups=(), current_teams=("engineering",))
    assert reconcile(left, MAPPING, now=NOW).teams == ()


def test_a_removed_group_is_reported_as_a_change():
    left = snapshot(groups=(), current_teams=("engineering",))
    assert reconcile(left, MAPPING, now=NOW).changed is True


def test_losing_every_team_is_called_out():
    left = snapshot(groups=(), current_teams=("engineering",))
    assert reconcile(left, MAPPING, now=NOW).removed_all is True


def test_keeping_a_team_is_not_called_out():
    assert reconcile(snapshot(), MAPPING, now=NOW).removed_all is False


def test_a_role_group_grants_the_role():
    promoted = snapshot(groups=("eng-all", "platform-admins"))
    assert "platform-admin" in reconcile(promoted, MAPPING, now=NOW).roles


def test_losing_a_role_group_removes_the_role():
    demoted = snapshot(groups=("eng-all",), current_roles=("platform-admin",))
    assert reconcile(demoted, MAPPING, now=NOW).roles == ()


def test_a_group_with_no_mapping_is_ignored():
    extra = snapshot(groups=("eng-all", "social-club"))
    assert reconcile(extra, MAPPING, now=NOW).teams == ("engineering",)


def test_an_unmapped_group_is_still_reported_so_it_can_be_mapped():
    extra = snapshot(groups=("eng-all", "social-club"))
    assert "social-club" in reconcile(extra, MAPPING, now=NOW).unmapped


def test_a_stale_snapshot_changes_nothing():
    old = snapshot(groups=(), taken_at=NOW - timedelta(hours=25))
    assert reconcile(old, MAPPING, now=NOW).changed is False


def test_a_stale_snapshot_says_why_it_was_ignored():
    old = snapshot(groups=(), taken_at=NOW - timedelta(hours=25))
    assert "stale" in reconcile(old, MAPPING, now=NOW).reason


def test_a_stale_snapshot_leaves_the_existing_teams_in_place():
    old = snapshot(groups=(), taken_at=NOW - timedelta(hours=25))
    assert reconcile(old, MAPPING, now=NOW).teams == ("engineering",)


def test_a_snapshot_from_the_future_is_not_trusted():
    ahead = snapshot(groups=(), taken_at=NOW + timedelta(hours=1))
    assert reconcile(ahead, MAPPING, now=NOW).changed is False


def test_teams_are_reported_in_a_stable_order():
    joined = snapshot(groups=("fin-all", "eng-all"))
    assert reconcile(joined, MAPPING, now=NOW).teams == ("engineering", "finance")


def test_the_person_is_carried_through():
    assert reconcile(snapshot(), MAPPING, now=NOW).person == "ana"


def test_a_snapshot_without_a_person_is_refused():
    with pytest.raises(ValueError):
        snapshot(person=" ")


def test_a_mapping_that_sends_one_group_to_two_teams_is_refused():
    with pytest.raises(ValueError):
        Mapping(
            teams_by_group={"eng-all": "engineering"},
            roles_by_group={"eng-all": "approver"},
        )
