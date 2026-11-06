"""Checking that a read or write stays inside the asker's own data."""

from __future__ import annotations

import pytest

from agent.src.security.scope_check import (
    Access,
    Asker,
    Record,
    Refusal,
    may_access,
)

ASKER = Asker(person="ana", org="acme", teams=("finance",))

OWN = Record(org="acme", owner="ana", team="finance", visibility="private")
TEAM = Record(org="acme", owner="bo", team="finance", visibility="team")
OTHER_TEAM = Record(org="acme", owner="cy", team="legal", visibility="team")
OTHER_ORG = Record(org="globex", owner="dee", team="finance", visibility="team")


def test_a_person_may_read_their_own_record():
    assert may_access(ASKER, OWN, Access.READ).permitted is True


def test_a_person_may_write_their_own_record():
    assert may_access(ASKER, OWN, Access.WRITE).permitted is True


def test_a_person_may_read_a_record_shared_with_their_team():
    assert may_access(ASKER, TEAM, Access.READ).permitted is True


def test_a_person_may_not_write_someone_elses_record():
    assert may_access(ASKER, TEAM, Access.WRITE).refusal is Refusal.NOT_OWNER


def test_a_person_may_not_read_another_teams_record():
    assert may_access(ASKER, OTHER_TEAM, Access.READ).refusal is Refusal.WRONG_TEAM


def test_a_person_may_not_read_another_organisations_record():
    assert may_access(ASKER, OTHER_ORG, Access.READ).refusal is Refusal.WRONG_ORG


def test_another_organisation_outranks_every_other_reason():
    assert may_access(ASKER, OTHER_ORG, Access.WRITE).refusal is Refusal.WRONG_ORG


def test_a_cross_organisation_refusal_says_nothing_about_the_record():
    refused = may_access(ASKER, OTHER_ORG, Access.READ)
    assert "dee" not in refused.reason and "finance" not in refused.reason


def test_a_private_record_belonging_to_someone_else_is_not_readable():
    private = Record(org="acme", owner="bo", team="finance", visibility="private")
    assert may_access(ASKER, private, Access.READ).refusal is Refusal.NOT_OWNER


def test_an_organisation_wide_record_is_readable_by_any_member():
    wide = Record(org="acme", owner="cy", team="legal", visibility="org")
    assert may_access(ASKER, wide, Access.READ).permitted is True


def test_an_organisation_wide_record_is_still_not_writable_by_anyone():
    wide = Record(org="acme", owner="cy", team="legal", visibility="org")
    assert may_access(ASKER, wide, Access.WRITE).permitted is False


def test_an_administrator_may_read_across_teams():
    admin = Asker(person="cy", org="acme", teams=(), roles=("platform-admin",))
    assert may_access(admin, OTHER_TEAM, Access.READ).permitted is True


def test_an_administrator_may_not_read_across_organisations():
    admin = Asker(person="cy", org="acme", teams=(), roles=("platform-admin",))
    assert may_access(admin, OTHER_ORG, Access.READ).refusal is Refusal.WRONG_ORG


def test_an_administrator_may_not_write_someone_elses_record():
    admin = Asker(person="cy", org="acme", teams=(), roles=("platform-admin",))
    assert may_access(admin, TEAM, Access.WRITE).permitted is False


def test_deleting_is_held_to_the_same_bar_as_writing():
    assert may_access(ASKER, TEAM, Access.DELETE).refusal is Refusal.NOT_OWNER


def test_a_person_may_delete_their_own_record():
    assert may_access(ASKER, OWN, Access.DELETE).permitted is True


def test_an_asker_without_an_organisation_is_refused():
    with pytest.raises(ValueError):
        Asker(person="ana", org=" ", teams=())


def test_a_record_with_an_unknown_visibility_is_refused():
    with pytest.raises(ValueError):
        Record(org="acme", owner="ana", team="finance", visibility="everyone")
