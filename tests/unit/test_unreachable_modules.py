"""Code that is written, tested, and reached by nothing."""

from __future__ import annotations

import ast
import pathlib
from functools import lru_cache

CEILING = 117

REPO = pathlib.Path(__file__).resolve().parents[2]
ROOT = REPO / "services" / "agent"

LOADED_BY_NAME = {
    "aegra/http_app.py",
    "aegra/entrypoint.py",
    "cli/main.py",
    # `harness eval-worker` runs this as `python -m`; see
    # cli/serve.py:eval_worker_command.
    "src/evals/worker.py",
    # Spawned as a subprocess, by path, from
    # src/evals/runs.py:_run_eval_pattern_sync.
    "src/evals/lightspeed_runner.py",
}


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


def _dotted(path: pathlib.Path) -> str:
    """The dotted name a module is imported by."""
    relative = path.resolve().relative_to(ROOT.parent)
    return ".".join(relative.with_suffix("").parts)


@lru_cache(maxsize=1)
def unreachable() -> tuple[pathlib.Path, ...]:
    """Modules nothing in the product mentions but themselves."""
    sources: dict[pathlib.Path, str] = {}
    for base in (ROOT, REPO / "scripts"):
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                sources[path.resolve()] = path.read_text(encoding="utf-8")
            except OSError:
                continue

    modules = [
        path
        for path in sorted(ROOT.rglob("*.py"))
        if "__pycache__" not in path.parts
        and path.name != "__init__.py"
        and str(path.relative_to(ROOT)) not in LOADED_BY_NAME
    ]

    importers: dict[str, set[pathlib.Path]] = {}
    for other, text in sources.items():
        for name in imports_in(text):
            importers.setdefault(name, set()).add(other)

    found = []
    for path in modules:
        mine = path.resolve()
        by = importers.get(_dotted(path), set())
        if not (by - {mine}):
            found.append(path.relative_to(ROOT))
    return tuple(found)


def test_the_pile_does_not_grow():
    found = unreachable()
    assert len(found) <= CEILING, (
        f"{len(found)} unreachable modules, up from {CEILING}. "
        "A module with tests and no callers passes every check and does "
        "nothing. Wire it up or delete it; do not raise this number.\n"
        + "\n".join(f"  {p}" for p in found[:20])
    )


def test_the_measurement_still_works():
    """A sweep that finds nothing would pass forever."""
    assert unreachable(), "the sweep found nothing, which is not plausible"


def test_the_ceiling_is_not_far_above_the_truth():
    assert len(unreachable()) >= CEILING - 5, (
        f"only {len(unreachable())} now; lower CEILING to match"
    )


def test_the_list_is_written_down_where_somebody_will_read_it():
    """A number in a test is a number nobody sees."""
    doc = REPO / "docs" / "development" / "unreachable.md"
    assert doc.is_file()


def test_the_note_says_why_they_were_not_simply_deleted():
    doc = (REPO / "docs" / "development" / "unreachable.md").read_text()
    assert "staged work" in doc
