"""No route hands back a credential."""

from __future__ import annotations

import ast
import pathlib

import pytest

ROUTES = pathlib.Path(__file__).resolve().parents[3] / "services" / "agent" / "aegra"

SECRET_NAMES = (
    "access_token",
    "refresh_token",
    "client_secret",
    "api_key",
    "private_key",
    "password",
    "secret",
)

SAFE = ("has_", "_set", "_present", "_configured", "missing", "needs_")


def _returned_keys(path: pathlib.Path) -> set[str]:
    """Every literal dictionary key a module builds."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()

    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys |= {
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
    return keys


def _model_fields(path: pathlib.Path) -> set[str]:
    """Every annotated field on a model class in this module."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()

    fields: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if isinstance(statement, ast.AnnAssign) and isinstance(
                statement.target, ast.Name
            ):
                fields.add(statement.target.id)
    return fields


def _route_modules() -> list[pathlib.Path]:
    return sorted(
        path
        for path in ROUTES.glob("*.py")
        if path.name.endswith(("_routes.py", "feedback.py"))
    )


class TestTheSweepIsWorthRunning:
    def test_there_are_modules_to_read(self):
        assert len(_route_modules()) >= 15

    def test_it_can_see_the_keys_they_build(self):
        keys = set()
        for path in _route_modules():
            keys |= _returned_keys(path)
        assert len(keys) >= 50

    def test_it_can_see_the_model_classes_too(self):
        fields = set()
        for path in _route_modules():
            fields |= _model_fields(path)
        assert len(fields) >= 20


class TestNoHandlerBuildsASecretIntoAResponse:
    @pytest.mark.parametrize("path", _route_modules(), ids=lambda p: p.name)
    def test_it_returns_nothing_credential_shaped(self, path):
        offenders = sorted(
            key
            for key in _returned_keys(path) | _model_fields(path)
            if any(name in key.lower() for name in SECRET_NAMES)
            and not any(hint in key.lower() for hint in SAFE)
        )
        assert offenders == [], (
            f"{path.name} builds a response carrying {offenders}. A secret "
            "reaches this system to be used, not to be read back."
        )


def _offending(path: pathlib.Path) -> list[str]:
    return sorted(
        key
        for key in _returned_keys(path) | _model_fields(path)
        if any(name in key.lower() for name in SECRET_NAMES)
        and not any(hint in key.lower() for hint in SAFE)
    )


class TestTheSweepCanActuallyFail:
    """Planted leaks, because a green sweep proves nothing alone."""

    def test_a_token_in_a_dictionary_is_caught(self, tmp_path):
        leak = tmp_path / "x_routes.py"
        leak.write_text('def f():\n    return {"access_token": t}\n')
        assert _offending(leak) == ["access_token"]

    def test_a_token_on_a_model_class_is_caught(self, tmp_path):
        leak = tmp_path / "y_routes.py"
        leak.write_text("class Out:\n    refresh_token: str\n")
        assert _offending(leak) == ["refresh_token"]

    def test_a_nested_response_is_caught(self, tmp_path):
        leak = tmp_path / "z_routes.py"
        leak.write_text('def f():\n    return {"auth": {"client_secret": s}}\n')
        assert _offending(leak) == ["client_secret"]

    def test_saying_one_is_present_is_allowed(self, tmp_path):
        fine = tmp_path / "w_routes.py"
        fine.write_text("class Out:\n    has_api_key: bool\n")
        assert _offending(fine) == []

    def test_a_field_merely_about_a_secret_is_allowed(self, tmp_path):
        fine = tmp_path / "v_routes.py"
        fine.write_text("class Out:\n    api_key_configured: bool\n")
        assert _offending(fine) == []
