"""The TEST-3 check finds tautologies and spares determinism tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ci"))

import tautological_asserts as check  # noqa: E402


def _findings(source: str, tmp_path, monkeypatch) -> list[tuple[str, int, str]]:
    (tmp_path / "test_sample.py").write_text(source)
    monkeypatch.setattr(check, "TESTS", tmp_path)
    monkeypatch.setattr(check, "ROOT", tmp_path)
    return check.tautologies()


class TestTheRepositoryNow:
    def test_it_is_clean(self):
        assert check.tautologies() == []


class TestWhatItCatches:
    @pytest.mark.parametrize(
        "line",
        [
            "assert True",
            "assert 1",
            "assert 'yes'",
        ],
    )
    def test_a_truthy_literal(self, line, tmp_path, monkeypatch):
        found = _findings(f"def test_a():\n    {line}\n", tmp_path, monkeypatch)
        assert found, line

    def test_a_value_compared_with_itself(self, tmp_path, monkeypatch):
        found = _findings(
            "def test_a():\n    taken = 1\n    assert taken == taken\n",
            tmp_path,
            monkeypatch,
        )
        assert found
        assert "compares a value with itself" in found[0][2]


class TestWhatItLeavesAlone:
    def test_a_determinism_check(self, tmp_path, monkeypatch):
        """`f(x) == f(x)` is two calls, and it can fail."""
        found = _findings(
            "def test_a():\n    assert fingerprint(shape()) == fingerprint(shape())\n",
            tmp_path,
            monkeypatch,
        )
        assert found == []

    def test_a_method_called_twice(self, tmp_path, monkeypatch):
        found = _findings(
            "def test_a():\n    assert thing.key() == thing.key()\n",
            tmp_path,
            monkeypatch,
        )
        assert found == []

    @pytest.mark.parametrize(
        "line",
        [
            "assert False",
            "assert 0",
            "assert x == y",
            "assert mock.called",
        ],
    )
    def test_an_assertion_that_can_fail(self, line, tmp_path, monkeypatch):
        assert _findings(f"def test_a():\n    {line}\n", tmp_path, monkeypatch) == []
