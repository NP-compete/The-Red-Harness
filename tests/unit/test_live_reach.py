"""Imported is not live, and the reachability ratchet cannot tell."""

from __future__ import annotations

import ast
import pathlib

import pytest

AGENT = pathlib.Path(__file__).resolve().parents[2] / "services" / "agent"
SCRIPTS = pathlib.Path(__file__).resolve().parents[2] / "scripts"

ENTRY_PREFIXES = (
    "agent.aegra",
    "agent.cli",
    "agent.src.workflows.entrypoint",
    # A serve role like the one above it — `harness eval-worker`
    # starts this with `python -m`, so nothing imports it and the
    # orchestration it reaches looks unreachable without this.
    "agent.src.evals.worker",
    "scripts",
)

GHOSTS = {
    "security.authority",
    "security.budget",
    "security.delegation",
    "security.trust",
}


def _module_name(path: pathlib.Path) -> str:
    """`pkg/__init__.py` is `pkg`, not `pkg.__init__`."""
    if path.is_relative_to(SCRIPTS):
        parts = path.relative_to(SCRIPTS.parent).with_suffix("").parts
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    parts = path.relative_to(AGENT).with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(("agent",) + parts)


def _import_graph() -> dict[str, set[str]]:
    """Every module, and the `agent` modules it imports."""
    graph: dict[str, set[str]] = {}
    for base in (AGENT, SCRIPTS):
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            found: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("agent"):
                        found.add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("agent"):
                            found.add(alias.name)
            graph[_module_name(path)] = found
    return graph


def _live(graph: dict[str, set[str]]) -> set[str]:
    """Everything reachable from an entry point, transitively."""
    seen = {name for name in graph if name.startswith(ENTRY_PREFIXES)}
    stack = list(seen)
    while stack:
        for target in graph.get(stack.pop(), ()):
            for candidate in (target, target.rsplit(".", 1)[0]):
                if candidate in graph and candidate not in seen:
                    seen.add(candidate)
                    stack.append(candidate)
    return seen


def _imported_by_anything(graph: dict[str, set[str]]) -> set[str]:
    found: set[str] = set()
    for targets in graph.values():
        for target in targets:
            for candidate in (target, target.rsplit(".", 1)[0]):
                if candidate in graph:
                    found.add(candidate)
    return found


@pytest.fixture(scope="module")
def graph() -> dict[str, set[str]]:
    return _import_graph()


class TestTheGraphIsReal:
    def test_the_tree_was_found(self, graph):
        assert len(graph) > 300, len(graph)

    def test_there_are_entry_points(self, graph):
        entries = [name for name in graph if name.startswith(ENTRY_PREFIXES)]
        assert len(entries) > 20, entries

    def test_a_package_import_resolves(self, graph):
        """The bug that cost three true findings, as a test."""
        assert "agent.src.capability" in graph, sorted(
            name for name in graph if "capability" in name
        )
        assert "agent.src.capability" in _live(graph)

    def test_something_obviously_live_is_live(self, graph):
        live = _live(graph)
        for name in (
            "agent.src.security.policy",
            "agent.src.security.fencing",
            "agent.src.guardrails.tool_proxy",
            "agent.src.routing.middleware",
            "agent.src.capability.tool_proxy",
            "agent.src.security.tool_call_check",
        ):
            assert name in live, name


class TestGhosts:
    """Imported, and reachable from nothing that starts."""

    def test_the_ghost_set_is_what_it_was(self, graph):
        live = _live(graph)
        imported = _imported_by_anything(graph)
        found = {
            name.replace("agent.src.", "")
            for name in graph
            if name.startswith("agent.src.") and name in imported and name not in live
        }
        assert found == GHOSTS, (
            f"ghosts changed: gone {sorted(GHOSTS - found)}, "
            f"new {sorted(found - GHOSTS)}. Fewer means something was "
            "wired up or deleted — lower GHOSTS. More means a module "
            "arrived that nothing can reach."
        )

    def test_the_hub_is_itself_unreachable(self, graph):
        assert "agent.src.security.guard" not in _live(graph)

    def test_a_ghost_still_looks_reachable_to_the_other_ratchet(self, graph):
        """The blind spot, stated as a test rather than a comment."""
        imported = _imported_by_anything(graph)
        assert "agent.src.security.authority" in imported
        assert "agent.src.security.authority" not in _live(graph)
