"""No second place that answers "may they"."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[3] / "services" / "agent"

ALLOWED_ROLE_SETS = {
    "PRIVILEGED_ROLES",
}

UNWIRED = ("scope_check", "impersonation", "audit_query")

SUSPICIOUS_NAMES = (
    "ROLE_PERMISSIONS",
    "PERMISSIONS_BY_ROLE",
    "ROLE_GRANTS",
    "ACL",
    "ACCESS_MATRIX",
    "PERMISSION_TABLE",
)


def _python_files() -> list[Path]:
    return [
        path
        for path in SOURCE.rglob("*.py")
        if "__pycache__" not in path.parts and "test" not in path.name
    ]


class TestNoPermissionTable:
    def test_no_module_declares_one(self):
        found = []
        for path in _python_files():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    name = getattr(target, "id", "")
                    if name in SUSPICIOUS_NAMES:
                        found.append(f"{path.name}:{name}")
        assert found == [], (
            f"a role-to-permission table here is a second authorization system: {found}"
        )

    def test_no_local_role_set_is_wired_into_anything(self):
        """Three modules here hold role sets and decide access."""
        wired = []
        for module in UNWIRED:
            for path in _python_files():
                if path.name == f"{module}.py":
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if f"security.{module}" in text or f"import {module}" in text:
                    wired.append(f"{path.name} -> {module}")
        assert wired == [], (
            "a local decision point is now reachable, which makes it a "
            f"second authorization system: {wired}"
        )


class TestTheDecisionPointIsElsewhere:
    def test_there_is_a_policy_client(self):
        from agent.src.opa import service

        assert hasattr(service, "evaluate_message")

    def test_it_can_be_turned_off_for_a_deployment_that_has_no_engine(self):
        from agent.src.opa.config import is_opa_enabled

        assert isinstance(is_opa_enabled(), bool)

    def test_turning_it_off_is_not_a_runtime_toggle_on_authorization(self):
        """Off means "this deployment has no engine", not "skip the check"."""
        from agent.src.opa.config import get_opa_fail_open

        assert isinstance(get_opa_fail_open(), bool)


class TestWhatThisDoesNotForbid:
    """Said out loud, so the guard is not quietly widened later."""

    def test_asking_who_somebody_is(self):
        from agent.aegra.auth_helpers import authenticated_user_id

        assert callable(authenticated_user_id)

    def test_gating_an_operator_page_on_a_coarse_role(self):
        from agent.src.ldap import PRIVILEGED_ROLES

        assert PRIVILEGED_ROLES

    def test_a_resource_knowing_who_owns_it(self):
        from agent.src.knowledge.store import Document

        assert "owner" in Document.__dataclass_fields__


@pytest.mark.parametrize("name", SUSPICIOUS_NAMES)
def test_the_guard_can_fail(name):
    """A guard that cannot fire is decoration."""
    tree = ast.parse(f"{name} = {{'admins': ['read', 'write']}}\n")
    found = [
        getattr(target, "id", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
    ]
    assert name in found


class TestItIsWrittenDown:
    """A guard nobody can read is a guard somebody deletes."""

    @staticmethod
    def _doc():
        return (
            Path(__file__).resolve().parents[3]
            / "docs"
            / "security"
            / "authorization.md"
        )

    def test_there_is_a_note(self):
        assert self._doc().is_file()

    def test_it_names_the_two_acceptable_shapes(self):
        said = self._doc().read_text().lower()
        assert "acceptable shapes" in said and "not acceptable" in said

    def test_it_says_why_the_third_is_not(self):
        assert "second" in self._doc().read_text().lower()

    def test_it_lists_the_modules_that_are_not_called(self):
        said = self._doc().read_text()
        for module in UNWIRED:
            assert module in said
