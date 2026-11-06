"""Working out who a run is acting as, before anything else happens."""

from __future__ import annotations

import pytest

from agent.src.security.run_identity import identify

CLAIMS = {"sub": "someone@example.com", "groups": ["sre", "platform-admin"]}


def test_a_signed_in_person_is_themselves():
    who = identify(claims=CLAIMS)
    assert who.subject == "someone@example.com"
    assert who.delegated_by is None


def test_their_groups_come_through():
    assert identify(claims=CLAIMS).groups == ("sre", "platform-admin")


def test_groups_are_optional():
    assert identify(claims={"sub": "a@example.com"}).groups == ()


def test_an_unauthenticated_request_has_no_identity():
    assert identify(claims=None) is None


def test_claims_without_a_subject_are_not_an_identity():
    assert identify(claims={"groups": ["sre"]}) is None


def test_a_blank_subject_is_not_an_identity():
    assert identify(claims={"sub": "   "}) is None


def test_a_scheduled_run_acts_for_whoever_scheduled_it():
    who = identify(claims=None, agent="ticket-triage", granted_by="someone@example.com")
    assert who.subject == "ticket-triage"
    assert who.delegated_by == "someone@example.com"


def test_a_scheduled_run_with_no_granter_is_refused():
    assert identify(claims=None, agent="ticket-triage") is None


def test_a_person_is_never_overridden_by_an_agent_name():
    who = identify(claims=CLAIMS, agent="ticket-triage", granted_by="other@example.com")
    assert who.subject == "someone@example.com"
    assert who.delegated_by is None


@pytest.mark.parametrize("field", ["token", "password", "secret"])
def test_no_credential_is_carried_on_the_identity(field):
    assert not hasattr(identify(claims=CLAIMS), field)
