"""The three fetch paths follow redirects by hand. Keep it that way."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

AGENT = Path(__file__).resolve().parents[3] / "services" / "agent"

FETCHERS = {
    "aegra/mcp_routes.py": "check_url",
    "aegra/mcp_oauth_handlers.py": "check_url",
    "src/knowledge/fetch.py": "assert_safe_url",
}


def _source(relative: str) -> str:
    return (AGENT / relative).read_text(encoding="utf-8")


def _follow_redirects_settings(source: str) -> list[object]:
    """Every `follow_redirects=` passed to a call, as its value."""
    found: list[object] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "follow_redirects":
                value = keyword.value
                found.append(
                    value.value if isinstance(value, ast.Constant) else "not-a-literal"
                )
    return found


@pytest.mark.parametrize("relative", sorted(FETCHERS))
class TestEachHopIsCheckedWhereItIsMade:
    def test_the_file_was_read(self, relative: str):
        assert len(_source(relative)) > 1000

    def test_the_client_does_not_follow_redirects_for_us(self, relative: str):
        settings = _follow_redirects_settings(_source(relative))
        assert settings, (
            f"{relative} no longer passes follow_redirects at all. httpx "
            "defaults to not following, so this still works — but the "
            "default is the thing somebody flips, and the three paths say "
            "it in writing."
        )
        assert True not in settings, (
            f"{relative} lets the client follow a redirect on its own. The "
            "first address is checked and nothing after it is; that is the "
            "bug all three of these loops were written to close."
        )

    def test_it_validates_before_each_hop(self, relative: str):
        text = _source(relative)
        assert FETCHERS[relative] in text, (
            f"{relative} no longer calls {FETCHERS[relative]}. Following "
            "redirects by hand is only a control if each one is checked."
        )

    def test_the_hops_are_bounded(self, relative: str):
        text = _source(relative)
        assert re.search(r"for _ in range\(\s*\w*MAX_\w+", text), (
            f"{relative} follows redirects in a loop with no ceiling on it."
        )


class TestTheCheckIsInsideTheLoop:
    """A validation before the loop is the bug, spelled differently."""

    @pytest.mark.parametrize("relative", sorted(FETCHERS))
    def test_the_validation_call_is_in_the_loop_body(self, relative: str):
        tree = ast.parse(_source(relative))
        wanted = FETCHERS[relative]

        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call):
                    name = inner.func
                    if isinstance(name, ast.Name) and name.id == wanted:
                        return
                    if isinstance(name, ast.Attribute) and name.attr == wanted:
                        return

        raise AssertionError(
            f"{relative} calls {wanted}, but not inside the loop that "
            "follows the redirects. Checking once and then looping is the "
            "same hole as letting the client follow them."
        )


class TestTheUnwiredCopyStaysUnwired:
    """`redirect_safety` is kept, and kept out of the live paths."""

    def test_no_production_module_imports_it(self):
        importers = []
        for path in AGENT.rglob("*.py"):
            if "redirect_safety" in path.read_text(encoding="utf-8"):
                importers.append(path.relative_to(AGENT).as_posix())
        assert not importers, (
            f"{importers} reaches for security/redirect_safety. If it is "
            "becoming the shared helper, move all three paths onto it and "
            "rewrite this file against it — do not wire up a fourth answer."
        )

    def test_the_module_is_still_there_for_its_test(self):
        assert (AGENT / "src" / "security" / "redirect_safety.py").exists(), (
            "redirect_safety was deleted. Its only importer, "
            "tests/unit/aegra/test_oauth_metadata_redirects.py, is the only "
            "behavioural test of per-hop revalidation in the tree — delete "
            "the module and that goes with it."
        )
