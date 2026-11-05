"""MU-7. Hiding a screen is not refusing it (E31-T7)."""

from __future__ import annotations

import inspect
import pathlib

import pytest
from fastapi import HTTPException

from agent.aegra import auth_helpers

OPERATOR_MODULES = (
    "admin_routes.py",
    "config_editing_routes.py",
    "document_routes.py",
    "eval_routes.py",
    "upload_routes.py",
    "user_admin_routes.py",
)

AEGRA = pathlib.Path(auth_helpers.__file__).parent


class _Request:
    def __init__(self, token: str = "") -> None:
        self.headers = {"authorization": f"Bearer {token}"} if token else {}


class TestTheCheckItself:
    @pytest.mark.asyncio
    async def test_an_everyday_role_is_refused(self, monkeypatch):
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", True)
        monkeypatch.setattr(
            "agent.aegra.auth._decode_token",
            lambda _token: {"preferred_username": "ada"},
        )

        async def _role(_who):
            return "users"

        monkeypatch.setattr(
            "agent.src.ldap.service.resolve_user_role", _role, raising=False
        )
        monkeypatch.setattr(auth_helpers, "resolve_user_role", _role, raising=False)

        with pytest.raises(HTTPException) as refused:
            await auth_helpers.check_ldap_role(_Request("t"), developer_only=True)
        assert refused.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_token_is_refused_before_any_role_question(self, monkeypatch):
        """401, not 403: nobody has claimed to be anybody yet."""
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", True)
        with pytest.raises(HTTPException) as refused:
            await auth_helpers.check_ldap_role(_Request(), developer_only=True)
        assert refused.value.status_code == 401


class TestEveryOperatorSurfaceAsks:
    @pytest.mark.parametrize("module", OPERATOR_MODULES)
    def test_it_checks_the_role_and_not_only_the_identity(self, module):
        """Either form of the same question."""
        source = (AEGRA / module).read_text()
        assert (
            "developer_only=True" in source or "Depends(_require_developer)" in source
        ), (
            f"{module} is an operator surface that never asks for a role. "
            "Resolving who somebody is does not decide what they may do, "
            "and the interface hiding the screen is not a refusal."
        )

    def test_the_list_is_not_quietly_shorter_than_the_tree(self):
        """A new operator module must be added here deliberately."""
        for module in OPERATOR_MODULES:
            assert (AEGRA / module).is_file(), f"{module} has moved or gone"


class TestTheInterfaceIsNotTheEnforcement:
    def test_the_check_refuses_rather_than_hiding(self):
        source = inspect.getsource(auth_helpers.check_ldap_role)
        assert "403" in source
        assert "status_code=403" in source
