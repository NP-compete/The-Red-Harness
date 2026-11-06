"""The CI image runs the tools this repository pins (E26-T4)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "harness:ci"

WATCHED = ("pytest", "ruff", "mypy", "pytest-asyncio")


def pinned() -> dict[str, str]:
    """The version pinned for each watched dependency."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    specs: list[str] = list(data["project"].get("dependencies") or [])
    for group in (data["project"].get("optional-dependencies") or {}).values():
        specs += [one for one in group if isinstance(one, str)]
    found = {}
    for spec in specs:
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", spec)
        if match:
            found[match.group(1).lower()] = match.group(2)
    return found


def installed(image: str = IMAGE) -> dict[str, str]:
    """What the image actually has, asked of the image."""
    script = (
        "import importlib.metadata as m, json\n"
        f"out = {{}}\n"
        f"for name in {list(WATCHED)!r}:\n"
        "    try:\n"
        "        out[name] = m.version(name)\n"
        "    except Exception:\n"
        "        out[name] = ''\n"
        "print(json.dumps(out))\n"
    )
    found = subprocess.run(
        [
            "podman",
            "run",
            "--rm",
            "--entrypoint",
            "/app/.venv/bin/python",
            image,
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if found.returncode != 0:
        raise SystemExit(f"Could not read {image}: {found.stderr.strip()[:200]}")
    parsed: dict[str, str] = json.loads(found.stdout.strip().splitlines()[-1])
    return parsed


def main() -> int:
    """Check that the installed toolchain matches what is pinned."""
    want, have = pinned(), installed()
    problems = []
    for name in WATCHED:
        expected = want.get(name)
        actual = have.get(name)
        if not expected:
            problems.append(f"{name}: not pinned in pyproject.toml")
        elif not actual:
            problems.append(f"{name}: not installed in {IMAGE}")
        elif actual != expected:
            problems.append(f"{name}: image has {actual}, pyproject pins {expected}")

    for name in WATCHED:
        print(
            f"  {name:<16} {have.get(name) or '—':<10} (pinned {want.get(name) or '—'})"
        )
    if problems:
        print(f"\n{IMAGE} does not match this repository:", file=sys.stderr)
        for one in problems:
            print(f"  {one}", file=sys.stderr)
        return 1
    print(f"\n{IMAGE} runs the tools this repository pins.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
