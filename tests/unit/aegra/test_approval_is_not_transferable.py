"""Nobody approves somebody else's pending action."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest


def _run_api_source() -> str:
    """The run API as shipped, read rather than imported."""
    import aegra_api.api.runs as runs

    return inspect.getsource(runs)


def _comparisons(source: str) -> list[str]:
    """Every comparison of a thread's owner against the caller."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Compare):
            continue
        text = ast.unparse(node)
        if "user_id" in text and "identity" in text:
            found.append(text)
    return found


class TestTheRuleIsStillThere:
    def test_the_run_api_compares_the_thread_owner_to_the_caller(self):
        found = _comparisons(_run_api_source())
        assert found, (
            "Nothing in the run API compares a thread's owner to the caller. "
            "Either the check moved, or an upgrade removed it — and with it "
            "the rule that one person cannot answer another's approval."
        )

    def test_it_is_checked_where_runs_are_created(self):
        assert len(_comparisons(_run_api_source())) >= 2

    def test_the_comparison_is_an_inequality_that_refuses(self):
        assert any("!=" in one for one in _comparisons(_run_api_source()))


class TestTheCheckCanFail:
    """A planted source, because a green sweep proves nothing alone."""

    def test_source_with_no_ownership_comparison_is_caught(self):
        assert _comparisons("def create(user):\n    return 1\n") == []

    def test_a_comparison_of_something_else_does_not_count(self):
        assert _comparisons("x = thread.title != user.name\n") == []

    def test_the_real_shape_is_recognised(self):
        planted = "x = existing_thread.user_id != user.identity\n"
        assert _comparisons(planted) == ["existing_thread.user_id != user.identity"]


class TestTheDependencyIsPinned:
    """An exact version, so the rule cannot drift in on an upgrade."""

    @pytest.mark.parametrize("package", ["aegra-api", "aegra-cli"])
    def test_it_is_pinned_exactly(self, package):
        pyproject = (Path(__file__).resolve().parents[3] / "pyproject.toml").read_text()
        assert f'"{package}==' in pyproject, (
            f"{package} is not pinned to an exact version, so the ownership "
            "rule asserted above could change without anybody choosing it."
        )
