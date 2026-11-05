"""No background task the garbage collector may eat (SCALE-5)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services" / "agent"

SCHEDULERS = {"create_task", "ensure_future"}


def dropped_tasks() -> list[tuple[str, int, str]]:
    """Scheduled coroutines whose task is discarded, as (path, line, what)."""
    found: list[tuple[str, int, str]] = []
    for path in sorted(SOURCE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - not ours to fix
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if isinstance(func, ast.Attribute) and func.attr in SCHEDULERS:
                found.append(
                    (
                        str(path.relative_to(ROOT)),
                        node.lineno,
                        f"{func.attr}(...)",
                    )
                )
    return found


def main() -> int:
    """Check that every scheduled coroutine keeps a reference to its task."""
    found = dropped_tasks()
    if not found:
        print("  every scheduled coroutine keeps a reference to its task")
        print("  (create_task and ensure_future, in services/agent/)")
        print("\nno background work can be collected mid-flight")
        return 0
    print("background tasks with no strong reference:", file=sys.stderr)
    for where, line, what in found:
        print(f"  {where}:{line}  {what}", file=sys.stderr)
    print(
        "\nKeep the task in a module-level set and discard it in a "
        "done-callback. The loop's reference is weak, so this one is the "
        "only thing stopping the collector.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
