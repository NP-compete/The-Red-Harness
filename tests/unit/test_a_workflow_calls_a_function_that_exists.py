"""Every `dagger call` in a workflow names a function (CI-10).

`e2e-report` was in the workflow and `e-2-e-report` is the function:
Dagger derives the CLI name from the Python one, and it splits on
digits. The step only runs `if: failure()`, so the first thing it
ever did was fail to produce the report somebody was already
waiting for — the diagnostic failing exactly when the diagnosis was
needed.

A name is the cheapest thing to get wrong and the cheapest to
check, so it is checked here rather than in a container.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
MODULE = ROOT / "ci" / "src" / "harness" / "main.py"

#: `dagger -m ci call <name>` or `dagger -m ci call <name> <verb>`.
CALL = re.compile(r"dagger\s+-m\s+ci\s+call\s+([a-z0-9-]+)")


def _cli_name(python_name: str) -> str:
    """What the Dagger CLI calls a function named `python_name`.

    Underscores become dashes, and a digit is its own word: `e2e` is
    `e-2-e`, which is ugly and is what it is.
    """
    spaced = python_name.replace("_", "-")
    spaced = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", "-", spaced)
    return spaced


def _functions() -> set[str]:
    """Every `@function` in the pipeline module, by CLI name."""
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))

    def named(decorator: ast.expr) -> str:
        if isinstance(decorator, ast.Call):
            decorator = decorator.func
        return getattr(decorator, "id", getattr(decorator, "attr", ""))

    return {
        _cli_name(node.name)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(named(d) == "function" for d in node.decorator_list)
    }


def test_the_module_is_there():
    """Without it every assertion below would hold vacuously."""
    assert MODULE.is_file()


def test_some_workflow_calls_dagger():
    """A regex that matches nothing would pass the test below."""
    text = " ".join(p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.y*ml"))
    assert CALL.search(text), "no workflow calls a Dagger function any more"


def test_every_call_names_a_function():
    known = _functions()
    stray: dict[str, str] = {}
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        for name in CALL.findall(path.read_text(encoding="utf-8")):
            if name not in known:
                stray[f"{path.name}:{name}"] = name
    assert not stray, (
        f"these name no Dagger function: {sorted(stray)}. "
        f"The module offers {sorted(known)}."
    )
