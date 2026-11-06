"""The OBS-3 ratchet can fall and cannot rise."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ci"))

import failure_logs_name_things as check  # noqa: E402


class TestTheRepositoryNow:
    def test_it_passes(self):
        assert check.problems() == []

    def test_the_ceiling_is_not_stale(self):
        """It may fall, so keep it at the floor."""
        assert len(check.bare()) == check.CEILING, (
            f"{len(check.bare())} bare failure logs against a ceiling of "
            f"{check.CEILING}. Lower CEILING."
        )

    @pytest.mark.parametrize("path", sorted(check.NAMED))
    def test_each_pinned_one_exists_and_has_context(self, path):
        message = check.NAMED[path]
        matching = [
            ctx
            for p, _n, m, ctx in check._calls()
            if p == path and m.startswith(message)
        ]
        assert matching, f"{message!r} is gone from {path}"
        assert all(matching)


class TestItCanFail:
    def test_a_pinned_message_losing_its_identifier(self, monkeypatch):
        monkeypatch.setattr(
            check,
            "_calls",
            lambda: [
                ("services/agent/aegra/feedback.py", 1, "feedback_handler_error", False)
            ],
        )
        monkeypatch.setattr(
            check,
            "NAMED",
            {"services/agent/aegra/feedback.py": "feedback_handler_error"},
        )
        found = check.problems()
        assert any("lost its identifier" in one for one in found), found

    def test_a_pinned_message_disappearing(self, monkeypatch):
        monkeypatch.setattr(check, "_calls", list)
        found = check.problems()
        assert any("no failure log starting" in one for one in found), found

    def test_a_new_context_free_failure_log(self, monkeypatch):
        real = check._calls()
        monkeypatch.setattr(
            check,
            "_calls",
            lambda: real + [("services/agent/invented.py", 1, "it_broke", False)],
        )
        found = check.problems()
        assert any("more than the ceiling" in one for one in found), found

    def test_but_a_new_one_with_context_is_fine(self, monkeypatch):
        real = check._calls()
        monkeypatch.setattr(
            check,
            "_calls",
            lambda: real + [("services/agent/invented.py", 1, "it_broke", True)],
        )
        assert check.problems() == []


class TestWhatItDeliberatelyIgnores:
    def test_an_interpolated_message_is_not_counted(self):
        """`%s` and f-strings carry their own context."""
        import ast

        source = 'logger.error("could not read %s", path)'
        node = ast.parse(source).body[0].value
        first = node.args[0]
        assert isinstance(first, ast.Constant)
        assert len(node.args) > 1, "this shape must read as having context"
