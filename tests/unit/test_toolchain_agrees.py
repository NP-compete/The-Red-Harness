"""One version of each tool, wherever it runs (E26-T4)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
PRE_COMMIT = ROOT / ".pre-commit-config.yaml"

SHARED = {
    "https://github.com/astral-sh/ruff-pre-commit": "ruff",
}

# mypy runs as a `language: system` hook so it is the project's own mypy,
# not a second copy pinned by a hook revision. There is no version to
# compare, and nothing to drift; this test checks that stays true.
SYSTEM_HOOKS = {"mypy"}


def _pinned() -> dict[str, str]:
    """Version pins from `pyproject.toml`, by distribution."""
    data = tomllib.loads(PYPROJECT.read_text())
    everything: list[str] = list(data["project"].get("dependencies") or [])
    for group in (data["project"].get("optional-dependencies") or {}).values():
        everything += [one for one in group if isinstance(one, str)]
    for group in (data.get("dependency-groups") or {}).values():
        everything += [one for one in group if isinstance(one, str)]
    found = {}
    for spec in everything:
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", spec)
        if match:
            found[match.group(1).lower()] = match.group(2)
    return found


def _hooks() -> dict[str, str]:
    """Hook revisions, by the distribution the hook runs."""
    data = yaml.safe_load(PRE_COMMIT.read_text()) or {}
    found = {}
    for repo in data.get("repos") or []:
        name = SHARED.get(str(repo.get("repo")))
        if name:
            found[name] = str(repo.get("rev", "")).lstrip("v")
    return found


class TestTheToolsAgree:
    @pytest.mark.parametrize("tool", sorted(SHARED.values()))
    def test_the_hook_runs_what_the_project_pins(self, tool):
        pinned, hooked = _pinned(), _hooks()
        assert tool in hooked, f"{tool} has no hook in .pre-commit-config.yaml"
        assert tool in pinned, f"{tool} is not pinned in pyproject.toml"
        assert hooked[tool] == pinned[tool], (
            f"{tool} is {pinned[tool]} in pyproject.toml and {hooked[tool]} in "
            ".pre-commit-config.yaml. Whichever ran last wins the argument "
            "about how the code should look."
        )

    @pytest.mark.parametrize("tool", sorted(SYSTEM_HOOKS))
    def test_a_system_hook_cannot_drift_from_the_pin(self, tool):
        """A `language: system` hook runs the pinned tool by construction."""
        data = yaml.safe_load(PRE_COMMIT.read_text()) or {}
        hooks = [
            hook
            for repo in data.get("repos") or []
            if str(repo.get("repo")) == "local"
            for hook in repo.get("hooks") or []
            if hook.get("id") == tool
        ]
        assert hooks, f"{tool} has no local hook in .pre-commit-config.yaml"
        assert hooks[0].get("language") == "system", (
            f"{tool} is a local hook but not `language: system`, so it runs "
            "some other copy than the one pyproject.toml pins."
        )
        assert tool in _pinned(), f"{tool} is not pinned in pyproject.toml"

    def test_both_files_actually_pin_something(self):
        assert _pinned() and _hooks()
