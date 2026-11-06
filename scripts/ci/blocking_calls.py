"""No blocking call inside a coroutine (PERF-7)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services" / "agent"

BLOCKING = {
    "time.sleep",
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.delete",
    "requests.request",
    "httpx.get",
    "httpx.post",
    "httpx.put",
    "httpx.delete",
    "httpx.request",
    "httpx.Client",
    "psycopg.connect",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_output",
    "urllib.request.urlopen",
}

BLOCKING_METHODS = {
    "read_text",
    "write_text",
    "read_bytes",
    "write_bytes",
}


def _dotted(node: ast.AST) -> str:
    """The dotted name of an attribute or name node."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def blocking_calls() -> list[tuple[str, int, str]]:
    """Blocking calls reachable inside a coroutine, as (path, line, what)."""
    found: list[tuple[str, int, str]] = []
    for path in sorted(SOURCE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - not ours to fix
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                name = _dotted(sub.func)
                if name in BLOCKING:
                    found.append((str(path.relative_to(ROOT)), sub.lineno, name))
                elif (
                    isinstance(sub.func, ast.Attribute)
                    and sub.func.attr in BLOCKING_METHODS
                ):
                    found.append(
                        (
                            str(path.relative_to(ROOT)),
                            sub.lineno,
                            f".{sub.func.attr}()",
                        )
                    )
    return found


def main() -> int:
    """Check that no blocking call sits inside an async def."""
    found = blocking_calls()
    if not found:
        print(f"  no blocking call inside an async def in {SOURCE.name}/")
        print("  (sleep, sync http, sync connect, subprocess, file read/write)")
        print("\nnothing on the request path holds the event loop")
        return 0
    print("blocking calls inside a coroutine:", file=sys.stderr)
    for where, line, what in found:
        print(f"  {where}:{line}  {what}", file=sys.stderr)
    print(
        "\nWrap each in `await asyncio.to_thread(...)`. A synchronous read "
        "here stops every other request on the pod, including the probes.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
