"""How much of the security package is wired to anything."""

from __future__ import annotations

import ast
import pathlib
from functools import lru_cache

CEILING = 52

AGENT = pathlib.Path(__file__).resolve().parents[3] / "services" / "agent"
SECURITY = AGENT / "src" / "security"


def imports_in(source: str) -> set[str]:
    """Every module this source imports, as dotted paths."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            for alias in node.names:
                found.add(f"{node.module}.{alias.name}")
    return found


@lru_cache(maxsize=1)
def _imported_anywhere() -> set[str]:
    """Everything production code imports, read once."""
    found: set[str] = set()
    for path in AGENT.rglob("*.py"):
        found |= imports_in(path.read_text(encoding="utf-8"))
    return found


def _module_name(path: pathlib.Path) -> str:
    relative = path.resolve().relative_to(AGENT.parent)
    return ".".join(relative.with_suffix("").parts)


def unreachable() -> list[str]:
    """Security modules nothing in the agent imports."""
    reached = _imported_anywhere()
    out: list[str] = []
    for path in sorted(SECURITY.glob("*.py")):
        if path.name == "__init__.py":
            continue
        name = _module_name(path)
        if name not in reached:
            out.append(path.stem)
    return out


class TestTheSweepIsWorthRunning:
    def test_there_are_modules_to_read(self):
        assert len(list(SECURITY.glob("*.py"))) >= 50

    def test_it_can_see_imports(self):
        assert len(_imported_anywhere()) >= 200

    def test_a_module_that_is_imported_is_not_reported(self):
        for wired in ("untrusted_reads", "secret_source", "fencing"):
            assert wired not in unreachable(), f"{wired} is imported and was missed"


class TestTheCheckCanFail:
    def test_a_name_in_a_comment_is_not_an_import(self):
        assert "agent.src.security.egress" not in imports_in(
            "# see agent.src.security.egress for the rule\n"
        )

    def test_a_real_import_is_seen(self):
        found = imports_in("from agent.src.security import egress\n")
        assert "agent.src.security.egress" in found

    def test_a_from_import_of_a_name_is_seen(self):
        found = imports_in("from agent.src.security.egress import allowed\n")
        assert "agent.src.security.egress" in found


class TestTheCountOnlyFalls:
    def test_it_has_not_grown(self):
        found = unreachable()
        assert len(found) <= CEILING, (
            f"{len(found)} security modules are not imported by anything, up "
            f"from {CEILING}. Either a module was added here without a "
            f"caller, or something that used to import one stopped. Both are "
            f"worth a moment: a rule with no caller is a second answer to a "
            f"question the live path is already answering.\n"
            f"Unreachable now:\n  " + "\n  ".join(found[:20])
        )

    def test_wiring_one_up_is_noticed(self):
        found = unreachable()
        assert len(found) >= CEILING - 5, (
            f"Only {len(found)} are unreachable now, against a ceiling of "
            f"{CEILING}. Lower the ceiling so it keeps biting."
        )
