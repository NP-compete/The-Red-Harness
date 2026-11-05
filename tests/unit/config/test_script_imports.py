"""Scripts must read the checkout they live in."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"


def _imports_the_package(path: Path) -> bool:
    text = path.read_text()
    return "import agent" in text or "from agent" in text


NEEDS_LOCAL = sorted(
    # `rglob`, not `glob`: the scripts were grouped into
    # config/, deploy/, evals/ and the rest, and a top-level
    # glob then matched nothing at all.
    str(path.relative_to(SCRIPTS))
    for path in SCRIPTS.rglob("*.py")
    # The import, not the word: `config/agent` is a path, and
    # matching it selects scripts that never import the package.
    if _imports_the_package(path)
    and not path.name.startswith("_")
    and "__pycache__" not in path.parts
)


def test_there_are_scripts_to_check():
    """A glob that matches nothing would pass every assertion below."""
    assert NEEDS_LOCAL


@pytest.mark.parametrize("name", NEEDS_LOCAL)
def test_the_script_puts_this_checkout_first(name: str):
    found = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy, sys;"
            f"sys.argv=[{name!r}];"
            f"runpy.run_path({str(SCRIPTS / name)!r}, run_name='probe');"
            "import agent.src.settings as s;"
            "print(s.__file__)",
        ],
        capture_output=True,
        text=True,
        cwd="/",
    )
    assert found.stdout.strip().startswith(str(REPO)), (
        f"{name} imported {found.stdout.strip() or found.stderr.strip()[:120]}, "
        f"which is outside {REPO}"
    )
