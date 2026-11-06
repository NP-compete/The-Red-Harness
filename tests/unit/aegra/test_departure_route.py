"""E31-T6. Closing somebody's account, over HTTP."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.aegra import user_admin_routes as routes


class _Request:
    headers: dict[str, str] = {}


class _Allowed:
    allowed = True
    reasons: list[str] = []
    why = ""
    field_class = "entitlement"


class _Refused:
    allowed = False
    reasons = ["role 'users' may not change 'entitlement' fields"]
    why = "role 'users' may not change 'entitlement' fields"
    field_class = "entitlement"


class _Doer:
    def __init__(self, failing: str | None = None) -> None:
        self.revoked: list[str] = []
        self.stopped: list[str] = []
        self.failing = failing

    async def revoke_connection(self, subject: str, server: str) -> None:
        if server == self.failing:
            raise RuntimeError("unreachable")
        self.revoked.append(server)

    async def stop_agent(self, name: str, reason: str) -> None:
        self.stopped.append(name)

    async def drop_collection(self, name: str) -> None:
        raise AssertionError("a departure must not drop collections here")


def _patches(decision, doer):
    return (
        patch.object(routes, "check_ldap_role", return_value="root"),
        patch.object(routes, "_role_of", return_value="admins"),
        patch.object(routes, "_configured_servers", return_value=("gitlab", "jira")),
        patch.object(routes, "decide", return_value=decision),
        patch(
            "agent.src.security.departure.LiveDeparture",
            return_value=doer,
        ),
    )


async def _post(decision, doer, **body):
    import contextlib

    with contextlib.ExitStack() as stack:
        for one in _patches(decision, doer):
            stack.enter_context(one)
        return await routes.carry_out_departure(
            _Request(), "ada", routes.DepartureAsked(**body)
        )


class TestPreview:
    @pytest.mark.asyncio
    async def test_it_changes_nothing(self):
        doer = _Doer()
        with (
            patch.object(routes, "check_ldap_role", return_value="root"),
            patch.object(
                routes, "_configured_servers", return_value=("gitlab", "jira")
            ),
            patch(
                "agent.aegra.my_data_routes._held_about",
                return_value={"documents": [{"id": "d1"}]},
            ),
        ):
            payload = await routes.preview_departure(_Request(), "ada")
        assert doer.revoked == []
        assert payload["revoke_connections"] == ["gitlab", "jira"]
        assert payload["personal_content"] == {"documents": 1}

    @pytest.mark.asyncio
    async def test_it_says_team_content_stays(self):
        """Taking it on the way out removes a colleague's runbook"""
        with (
            patch.object(routes, "check_ldap_role", return_value="root"),
            patch.object(routes, "_configured_servers", return_value=()),
            patch("agent.aegra.my_data_routes._held_about", return_value={}),
        ):
            payload = await routes.preview_departure(_Request(), "ada")
        assert "left in place" in payload["team_content"]


class TestCarryingItOut:
    @pytest.mark.asyncio
    async def test_a_refusal_revokes_nothing(self):
        doer = _Doer()
        answer = await _post(_Refused(), doer)
        assert answer.status_code == 403
        assert doer.revoked == []

    @pytest.mark.asyncio
    async def test_every_configured_server_is_revoked(self):
        """The candidate set, not the connected set: the token store"""
        doer = _Doer()
        payload = await _post(_Allowed(), doer)
        assert doer.revoked == ["gitlab", "jira"]
        assert payload["failed"] == []

    @pytest.mark.asyncio
    async def test_one_failing_step_does_not_stop_the_others(self):
        doer = _Doer(failing="gitlab")
        payload = await _post(_Allowed(), doer)
        assert doer.revoked == ["jira"]
        assert any("gitlab" in line for line in payload["failed"])

    @pytest.mark.asyncio
    async def test_personal_content_is_kept_unless_asked_for(self):
        """Revoking access is not deleting a person's work, and an"""
        doer = _Doer()
        payload = await _post(_Allowed(), doer)
        assert payload["personal_content_erased"] == "not asked for"

    @pytest.mark.asyncio
    async def test_it_says_it_cannot_see_delegations(self):
        """ "No agents were stopped" and "we cannot tell whether any"""
        doer = _Doer()
        payload = await _post(_Allowed(), doer)
        assert "no grant store" in payload["delegations"]
