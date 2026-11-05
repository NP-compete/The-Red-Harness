"""What the command line imports from the agent, as a ratchet (CLI-1)."""

from __future__ import annotations

import ast
from pathlib import Path

CLI = Path(__file__).resolve().parents[3] / "services" / "agent" / "cli"

ALWAYS_ALLOWED = {"agent.version"}

THE_PILE = {
    "agent.src.agent.config.inbound_pause",
    "agent.src.improvement.generate",
    "agent.src.improvement.mine",
    "agent.src.improvement.probe",
    "agent.src.improvement.propose",
    "agent.src.improvement.record",
}


def _reaches_inside() -> dict[str, set[str]]:
    """Every `agent.*` import outside `agent.cli`, by file."""
    found: dict[str, set[str]] = {}
    for path in sorted(CLI.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        reached = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                name = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("agent.") and not alias.name.startswith(
                        "agent.cli"
                    ):
                        reached.add(alias.name)
                continue
            else:
                continue
            if name.startswith("agent.") and not name.startswith("agent.cli"):
                reached.add(name)
        if reached:
            found[path.name] = reached
    return found


class TestTheBoundary:
    def test_the_walk_finds_something(self):
        assert _reaches_inside(), "no imports found at all; the walk is broken"

    def test_nothing_new_reaches_inside(self):
        reached = {m for names in _reaches_inside().values() for m in names}
        arrived = reached - THE_PILE - ALWAYS_ALLOWED
        assert not arrived, (
            f"the CLI now imports {sorted(arrived)} from the agent. CLI-1 says "
            "it speaks the public HTTP API only — add a route and call it, or "
            "if this is deliberate, change CLI-1's row in the PRD and add it "
            "to THE_PILE on purpose."
        )

    def test_the_pile_may_only_shrink(self):
        reached = {m for names in _reaches_inside().values() for m in names}
        gone = THE_PILE - reached
        assert not gone, (
            f"{sorted(gone)} is no longer imported — good. Remove it from "
            "THE_PILE so the ceiling comes down with it."
        )

    def test_the_version_import_is_not_counted_as_debt(self):
        reached = {m for names in _reaches_inside().values() for m in names}
        assert "agent.version" in reached
        assert not (ALWAYS_ALLOWED & THE_PILE)


class TestTheHalfThatHolds:
    """No datastore, which is CLI-1's other clause."""

    def test_no_cli_module_opens_a_connection(self):
        root = CLI.parents[1]
        for module in sorted(THE_PILE):
            path = root / Path(*module.split(".")).with_suffix(".py")
            if not path.exists():
                continue
            source = path.read_text()
            for forbidden in ("psycopg", "asyncpg", "import redis", "httpx"):
                assert forbidden not in source, (
                    f"{module} now reaches {forbidden}, and the CLI imports it — "
                    "CLI-1's 'never reaches a datastore' went with it"
                )
