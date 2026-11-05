"""Replacing a server's client credentials is an administrator's act."""

from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from agent.aegra import mcp_routes


class TestItAsksWhoIsCalling:
    def test_it_resolves_a_role_rather_than_only_a_flag(self):
        source = inspect.getsource(mcp_routes.mcp_reregister)
        assert "check_ldap_role" in source, (
            "mcp_reregister no longer resolves a role, so on a deployment "
            "that has enabled it any caller may replace an integration's "
            "client credentials."
        )

    def test_the_bar_is_the_developer_role(self):
        source = inspect.getsource(mcp_routes.mcp_reregister)
        assert "developer_only=True" in source


class TestTheFlagIsStillCheckedFirst:
    @pytest.mark.asyncio
    async def test_a_deployment_with_it_off_refuses_without_asking_who(
        self, monkeypatch
    ):
        asked: list[str] = []

        async def role(_request, developer_only=False):
            asked.append("asked")
            return "someone"

        monkeypatch.setattr("agent.aegra.auth_helpers.check_ldap_role", role)

        from agent.src.settings import settings

        monkeypatch.setattr(settings, "ENABLE_DCR_REREGISTER_API", False)

        answer = await mcp_routes.mcp_reregister("tracker", request=object())
        assert answer.status_code == 403
        assert asked == []


class TestAnUnauthorisedCallerGetsNowhere:
    @pytest.mark.asyncio
    async def test_the_registration_is_not_attempted(self, monkeypatch):
        from agent.src.settings import settings

        monkeypatch.setattr(settings, "ENABLE_DCR_REREGISTER_API", True)

        async def refuse(_request, developer_only=False):
            raise HTTPException(status_code=403, detail="not a developer")

        monkeypatch.setattr("agent.aegra.auth_helpers.check_ldap_role", refuse)

        reached: list[str] = []

        async def handler(name):
            reached.append(name)
            return {}

        monkeypatch.setattr(
            "agent.aegra.mcp_oauth_handlers.handle_mcp_reregister",
            handler,
        )

        with pytest.raises(HTTPException) as raised:
            await mcp_routes.mcp_reregister("tracker", request=object())
        assert raised.value.status_code == 403
        assert reached == [], "a re-registration was attempted for a refused caller"


class TestItMatchesTheOtherSelfAdministrationRoute:
    def test_clearing_the_data_tree_uses_the_same_bar(self):
        from agent.aegra import upload_routes

        theirs = inspect.getsource(upload_routes.clear_uploaded_data)
        mine = inspect.getsource(mcp_routes.mcp_reregister)
        assert "developer_only=True" in theirs
        assert "developer_only=True" in mine
