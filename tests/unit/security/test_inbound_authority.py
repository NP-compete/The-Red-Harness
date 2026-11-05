"""Whose authority an inbound run carries."""

from __future__ import annotations

import pytest

from agent.src.security.inbound_authority import (
    AuthorityRefused,
    authority_for,
)


class TestACallingPerson:
    """Mode one: the run behaves as if they had typed it."""

    def test_the_run_is_theirs(self):
        found = authority_for(mode="oauth", caller="alice", scope="act")
        assert found.user_id == "alice"

    def test_their_own_connections_apply(self):
        found = authority_for(mode="oauth", caller="alice", scope="act")
        assert found.may_use_connections is True

    def test_it_is_audited_as_them(self):
        found = authority_for(mode="oauth", caller="alice", scope="act")
        assert found.audit_as == "alice"

    def test_a_call_with_no_identity_is_refused(self):
        with pytest.raises(AuthorityRefused):
            authority_for(mode="oauth", caller="", scope="act")


class TestAServiceIdentity:
    """Mode two: automation with nobody behind it."""

    def test_the_run_is_not_a_persons(self):
        found = authority_for(mode="service_token", caller="nightly", scope="act")
        assert found.user_id != "nightly"

    def test_its_identity_is_marked_as_a_service(self):
        found = authority_for(mode="service_token", caller="nightly", scope="act")
        assert found.user_id.startswith("service:")

    def test_it_cannot_inherit_anybodys_connections(self):
        found = authority_for(mode="service_token", caller="nightly", scope="act")
        assert found.may_use_connections is False

    def test_it_is_still_attributed(self):
        found = authority_for(mode="service_token", caller="nightly", scope="act")
        assert found.audit_as == "nightly"

    def test_a_service_cannot_take_a_persons_namespace(self):
        found = authority_for(mode="service_token", caller="alice", scope="act")
        assert found.user_id != "alice"

    def test_a_call_with_no_identity_is_refused(self):
        with pytest.raises(AuthorityRefused):
            authority_for(mode="service_token", caller="", scope="act")


class TestTheDeputyIsUnreachable:
    """Not refused by a check — absent as an outcome."""

    @pytest.mark.parametrize(
        "mode", ["agent", "own", "agent_credentials", "self", "service_account", ""]
    )
    def test_no_mode_produces_the_agents_own_authority(self, mode):
        with pytest.raises(AuthorityRefused):
            authority_for(mode=mode, caller="alice", scope="act")

    def test_no_accepted_mode_leaves_the_identity_empty(self):
        for mode in ("oauth", "service_token"):
            assert authority_for(mode=mode, caller="x", scope="act").user_id


class TestScopeNarrowsItFurther:
    def test_a_read_tool_uses_no_connections_even_for_a_person(self):
        found = authority_for(mode="oauth", caller="alice", scope="read")
        assert found.may_use_connections is False

    def test_an_act_tool_may_for_a_person(self):
        found = authority_for(mode="oauth", caller="alice", scope="act")
        assert found.may_use_connections is True

    def test_scope_cannot_widen_a_service_identity(self):
        found = authority_for(mode="service_token", caller="nightly", scope="act")
        assert found.may_use_connections is False

    def test_an_unknown_scope_is_refused(self):
        with pytest.raises(AuthorityRefused):
            authority_for(mode="oauth", caller="alice", scope="whatever")


class TestWhatTheRunIsTold:
    def test_the_metadata_carries_the_identity(self):
        found = authority_for(mode="oauth", caller="alice", scope="act")
        assert found.as_metadata()["user_id"] == "alice"

    def test_the_metadata_says_it_came_from_outside(self):
        found = authority_for(mode="oauth", caller="alice", scope="act")
        assert found.as_metadata()["inbound"] is True

    def test_the_metadata_carries_who_to_attribute_it_to(self):
        found = authority_for(mode="service_token", caller="nightly", scope="act")
        assert found.as_metadata()["inbound_caller"] == "nightly"

    def test_the_metadata_says_whether_connections_apply(self):
        found = authority_for(mode="service_token", caller="nightly", scope="act")
        assert found.as_metadata()["may_use_connections"] is False
