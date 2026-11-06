"""A failure log names the thing that failed (OBS-3)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services"))

LOGGERS = ("logger", "log", "_logger")
LEVELS = ("error", "warning", "exception", "critical")

NAMED = {
    "services/agent/aegra/feedback.py": "feedback_handler_error",
    "services/agent/aegra/projects_routes.py": "project_delete_failed",
    "services/agent/aegra/mcp_resource_tools.py": "MCP resource request failed",
    "services/agent/aegra/mcp_crypto.py": "Failed to decrypt MCP secret",
}

CEILING = 51


def _calls() -> list[tuple[str, int, str, bool]]:
    """Every failure-log call: path, line, message, has context."""
    found: list[tuple[str, int, str, bool]] = []
    for path in sorted((ROOT / "services" / "agent").rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - not our file to fix
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Attribute) and fn.attr in LEVELS):
                continue
            if not (isinstance(fn.value, ast.Name) and fn.value.id in LOGGERS):
                continue
            if not node.args:
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                continue
            has_context = len(node.args) > 1 or bool(node.keywords)
            found.append(
                (
                    str(path.relative_to(ROOT)),
                    node.lineno,
                    first.value,
                    has_context,
                )
            )
    return found


def bare() -> list[tuple[str, int, str]]:
    """Every failure log whose message carries no context."""
    return [(p, n, m) for p, n, m, ctx in _calls() if not ctx]


def problems() -> list[str]:
    """Every pinned failure log whose message has drifted."""
    found: list[str] = []
    calls = _calls()

    for path, message in NAMED.items():
        matching = [
            (n, ctx) for p, n, m, ctx in calls if p == path and m.startswith(message)
        ]
        if not matching:
            found.append(
                f"{path}: no failure log starting {message!r}. It was fixed to "
                "carry an identifier; if it moved, move this entry."
            )
        elif not all(ctx for _n, ctx in matching):
            found.append(
                f"{path}: {message!r} lost its identifier. It reports that "
                "something failed and gives nowhere to look."
            )

    left = bare()
    if len(left) > CEILING:
        added = len(left) - CEILING
        found.append(
            f"{len(left)} failure logs carry a constant message and no "
            f"context, {added} more than the ceiling of {CEILING}. A new one "
            "is caught here because now is when you can still say whether it "
            "has an identifier to give — add it, or raise the ceiling with a "
            "reason."
        )
    return found


def main() -> int:
    """Check that failure logs name what actually failed."""
    left = bare()
    print(f"  {len(left)} constant-message failure log(s), ceiling {CEILING}")
    print(f"  {len(NAMED)} fixed and pinned")
    found = problems()
    if not found:
        if len(left) < CEILING:
            print(
                f"\nfewer than the ceiling — lower CEILING to {len(left)} to "
                "keep the ratchet tight"
            )
        print("\nevery pinned failure log still names its thing")
        return 0
    print("\nfailure logs that name nothing:", file=sys.stderr)
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
