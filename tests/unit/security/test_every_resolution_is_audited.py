"""Every secret resolution leaves a trail, including the failures."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.src.security import secret_source
from agent.src.security.secret_source import SecretUnavailable, resolve


def _recorded(calls):
    return [
        {"reference": call.kwargs.get("reference"), "found": call.kwargs.get("found")}
        for call in calls
    ]


class TestASourceThatAnswers:
    def test_a_success_is_recorded(self, monkeypatch):
        monkeypatch.setenv("SOMETHING", "a-value")
        with patch.object(secret_source, "emit_audit_event") as audit:
            resolve("env:SOMETHING")
        assert _recorded(audit.call_args_list) == [
            {"reference": "env:SOMETHING", "found": True}
        ]

    def test_an_absence_is_recorded(self, monkeypatch):
        monkeypatch.delenv("MISSING", raising=False)
        with patch.object(secret_source, "emit_audit_event") as audit:
            with pytest.raises(SecretUnavailable):
                resolve("env:MISSING")
        assert _recorded(audit.call_args_list) == [
            {"reference": "env:MISSING", "found": False}
        ]


class TestASourceThatRaises:
    """The case the trail was losing."""

    def _exploding(self, error: Exception):
        def read(_name: str) -> str | None:
            raise error

        return {"env": read}

    def test_a_refusal_is_still_recorded(self):
        with (
            patch.dict(
                secret_source.SOURCES, self._exploding(SecretUnavailable("no vault"))
            ),
            patch.object(secret_source, "emit_audit_event") as audit,
        ):
            with pytest.raises(SecretUnavailable):
                resolve("env:SOMETHING")
        assert _recorded(audit.call_args_list) == [
            {"reference": "env:SOMETHING", "found": False}
        ]

    def test_an_unexpected_failure_is_still_recorded(self):
        with (
            patch.dict(
                secret_source.SOURCES, self._exploding(RuntimeError("the network"))
            ),
            patch.object(secret_source, "emit_audit_event") as audit,
        ):
            with pytest.raises(Exception):
                resolve("env:SOMETHING")
        assert _recorded(audit.call_args_list) == [
            {"reference": "env:SOMETHING", "found": False}
        ]

    def test_the_refusal_still_reaches_the_caller(self):
        with patch.dict(
            secret_source.SOURCES, self._exploding(SecretUnavailable("no vault"))
        ):
            with pytest.raises(SecretUnavailable) as raised:
                resolve("env:SOMETHING")
        assert "no vault" in str(raised.value)


class TestTheValueNeverReachesTheTrail:
    def test_only_the_reference_is_recorded(self, monkeypatch):
        monkeypatch.setenv("SOMETHING", "the-actual-secret")
        with patch.object(secret_source, "emit_audit_event") as audit:
            resolve("env:SOMETHING")
        written = str(audit.call_args_list)
        assert "the-actual-secret" not in written
        assert "SOMETHING" in written


class TestEverySourceIsCovered:
    def test_the_read_is_wrapped_so_a_raise_cannot_skip_it(self):
        """The behaviour is covered above; this is the structure."""
        import ast
        import inspect
        import textwrap

        tree = ast.parse(textwrap.dedent(inspect.getsource(secret_source.resolve)))
        wrapped = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Try) and "read(name)" in ast.unparse(node)
        ]
        assert wrapped, "the source read is not wrapped, so a raise skips the trail"
        assert any(
            "_record(" in ast.unparse(handler) for handler in wrapped[0].handlers
        ), "nothing is recorded when the source raises"
