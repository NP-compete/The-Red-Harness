"""E9. What "authentication is off" means to the admin surface."""

from __future__ import annotations

import pytest

from agent.aegra import user_admin_routes as routes


class TestWithAuthenticationOff:
    @pytest.mark.asyncio
    async def test_the_actor_is_not_the_lowest_role(self, monkeypatch):
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", False)
        assert await routes._role_of("anybody") == routes.DEV_ROLE

    @pytest.mark.asyncio
    async def test_it_does_not_ask_the_directory(self, monkeypatch):
        """There is nothing to ask: no identity, no groups."""
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", False)

        async def _never(_who):
            raise AssertionError("the directory was asked with auth off")

        monkeypatch.setattr(
            "agent.src.ldap.service.resolve_user_role", _never, raising=False
        )
        assert await routes._role_of("anybody") == routes.DEV_ROLE

    def test_it_matches_what_the_gate_already_does(self):
        """`check_ldap_role` returns the dev user without checking"""
        import inspect

        from agent.aegra import auth_helpers

        assert "ENABLE_AUTH" in inspect.getsource(auth_helpers.check_ldap_role)


class TestWithAuthenticationOn:
    @pytest.mark.asyncio
    async def test_the_directory_decides(self, monkeypatch):
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", True)

        async def _says(_who):
            return "builders"

        monkeypatch.setattr(
            "agent.src.ldap.service.resolve_user_role", _says, raising=False
        )
        assert await routes._role_of("ada") == "builders"

    @pytest.mark.asyncio
    async def test_a_directory_that_cannot_answer_is_unknown(self, monkeypatch):
        """Unknown rather than assumed: the policy ranks `users`"""
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", True)

        async def _boom(_who):
            raise RuntimeError("ldap is down")

        monkeypatch.setattr(
            "agent.src.ldap.service.resolve_user_role", _boom, raising=False
        )
        assert await routes._role_of("ada") == "unknown"

    @pytest.mark.asyncio
    async def test_no_groups_configured_is_still_the_lowest_role(self, monkeypatch):
        """With authentication on and no groups, everybody is an"""
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", True)

        async def _none(_who):
            return None

        monkeypatch.setattr(
            "agent.src.ldap.service.resolve_user_role", _none, raising=False
        )
        assert await routes._role_of("ada") == "users"
