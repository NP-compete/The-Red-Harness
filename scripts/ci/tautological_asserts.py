"""No assertion that cannot fail (TEST-3)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"


def _calls_something(node: ast.AST) -> bool:
    """Whether the node contains a call."""
    return any(isinstance(one, ast.Call) for one in ast.walk(node))


def tautologies() -> list[tuple[str, int, str]]:
    """Assertions that cannot fail, as (path, line, why)."""
    found: list[tuple[str, int, str]] = []
    for path in sorted(TESTS.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - not ours to fix
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            test = node.test
            where = str(path.relative_to(ROOT))

            if isinstance(test, ast.Constant):
                if test.value:
                    found.append(
                        (where, node.lineno, f"assert {test.value!r} always passes")
                    )
                continue

            if (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
                and ast.dump(test.left) == ast.dump(test.comparators[0])
                and not _calls_something(test.left)
            ):
                found.append(
                    (
                        where,
                        node.lineno,
                        f"assert {ast.unparse(test)} compares a value with itself",
                    )
                )
    return found


def main() -> int:
    """Check that no assertion in the tests can only pass."""
    found = tautologies()
    if not found:
        print("  no assertion in tests/ compares a value with itself")
        print("  or asserts a truthy literal")
        print("\nevery assertion can fail")
        return 0
    print("assertions that cannot fail:", file=sys.stderr)
    for where, line, why in found:
        print(f"  {where}:{line}  {why}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
