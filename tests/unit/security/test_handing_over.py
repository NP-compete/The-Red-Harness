"""Handing a conversation to somebody else."""

from __future__ import annotations

import pytest

from agent.src.security.handing_over import hand_over
from agent.src.security.ownership_transfer import Thread, Transfer

THREAD = Thread(
    thread="t1",
    owner="amar",
    org="acme",
    readers=("amar",),
    guests=("contractor",),
    under_legal_hold=False,
    contains_personal_data=False,
)


def _handed(**kwargs):
    thread = kwargs.pop("thread", THREAD)
    transfer = Transfer(
        to=kwargs.pop("to", "bea"),
        to_org=kwargs.pop("to_org", "acme"),
        asked_by=kwargs.pop("asked_by", "amar"),
        accepted=kwargs.pop("accepted", True),
    )
    return hand_over(
        thread,
        transfer=transfer,
        servers_used=kwargs.pop("servers_used", ["gitlab", "jira"]),
        receiver_connections=kwargs.pop("receiver_connections", ["gitlab"]),
    )


class TestWhenItMayMove:
    def test_it_is_allowed(self):
        assert _handed().allowed is True

    def test_the_new_owner_gains_access(self):
        assert "bea" in _handed().gains_access

    def test_a_guest_does_not_come_along(self):
        assert "contractor" in _handed().guests_dropped

    def test_it_is_audited_with_both_names(self):
        said = _handed().audit_note
        assert "amar" in said and "bea" in said


class TestWhatTheNewOwnerMustDoThemselves:
    def test_they_are_told_what_to_connect(self):
        assert "jira" in _handed().needs_connecting

    def test_what_they_already_have_is_not_asked_for_again(self):
        assert "gitlab" not in _handed().needs_connecting

    def test_and_is_reported_as_already_theirs(self):
        assert "gitlab" in _handed().already_connected

    def test_a_receiver_with_everything_is_asked_for_nothing(self):
        found = _handed(receiver_connections=["gitlab", "jira"])
        assert found.needs_connecting == ()

    def test_the_warning_is_in_words(self):
        assert "jira" in _handed().warning


class TestWhatDoesNotMove:
    def test_no_credential_crosses(self):
        found = _handed()
        for field in (found.needs_connecting, found.already_connected):
            for name in field:
                assert "token" not in name and "secret" not in name

    def test_the_result_carries_no_secret_material(self):
        import dataclasses

        found = _handed()
        for field in dataclasses.fields(found):
            assert "token" not in field.name and "credential" not in field.name


class TestWhenItMayNot:
    def test_somebody_who_is_not_the_owner_cannot_give_it_away(self):
        assert _handed(asked_by="chen").allowed is False

    def test_it_cannot_leave_the_organisation(self):
        assert _handed(to_org="other").allowed is False

    def test_a_legal_hold_stops_it(self):
        held = Thread(**{**THREAD.__dict__, "under_legal_hold": True})
        assert _handed(thread=held).allowed is False

    def test_an_unaccepted_hand_off_waits_rather_than_failing(self):
        found = _handed(accepted=False)
        assert found.allowed is False and found.waiting is True

    def test_the_reason_is_given_in_every_case(self):
        for kwargs in ({"asked_by": "chen"}, {"to_org": "other"}, {"accepted": False}):
            assert _handed(**kwargs).reason

    def test_nothing_is_asked_of_a_receiver_who_is_not_getting_it(self):
        assert _handed(asked_by="chen").needs_connecting == ()


def test_handing_to_the_current_owner_is_refused_outright():
    with pytest.raises(ValueError):
        _handed(to="amar")


class TestItIsReachable:
    """Composing two orphans into a third is not progress."""

    @staticmethod
    def _client():
        from starlette.testclient import TestClient

        from agent.aegra.http_app import app

        return TestClient(app)

    @staticmethod
    def _ask(client, body, *, owner="amar"):
        from unittest.mock import patch

        with (
            patch("agent.aegra.handoff_routes._who", return_value=owner),
            patch(
                "agent.aegra.handoff_routes._thread_facts",
                return_value=THREAD,
            ),
            patch(
                "agent.aegra.handoff_routes._servers_used",
                return_value=["gitlab", "jira"],
            ),
            patch(
                "agent.aegra.handoff_routes._connections_of",
                return_value=["gitlab"],
            ),
        ):
            return client.post("/threads/t1/handover", json=body)

    def test_a_hand_off_can_be_asked_for(self):
        found = self._ask(self._client(), {"to": "bea", "accepted": True})
        assert found.status_code == 200

    def test_it_says_what_the_receiver_must_connect(self):
        found = self._ask(self._client(), {"to": "bea", "accepted": True}).json()
        assert "jira" in found["needs_connecting"]

    def test_somebody_who_is_not_the_owner_is_refused(self):
        found = self._ask(self._client(), {"to": "bea", "accepted": True}, owner="chen")
        assert found.status_code == 403

    def test_one_not_yet_accepted_is_not_an_error(self):
        found = self._ask(self._client(), {"to": "bea", "accepted": False})
        assert found.status_code == 200 and found.json()["waiting"] is True
