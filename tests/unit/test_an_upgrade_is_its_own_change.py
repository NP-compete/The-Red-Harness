"""Dependencies are pinned, and Aegra is not forked (COMPAT-1, COMPAT-3)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())

ALLOWED_LOOSE = {
    "en-core-web-lg": "pinned by the wheel URL, which carries 3.8.0",
    "python-multipart": "range resolved by uv.lock",
}


def _requirements() -> list[str]:
    found = list(PYPROJECT["project"].get("dependencies", []))
    for group in (PYPROJECT["project"].get("optional-dependencies") or {}).values():
        found.extend(group)
    return found


def _name_of(requirement: str) -> str:
    return re.split(r"[\s<>=!~@\[]", requirement.strip(), maxsplit=1)[0].lower()


class TestNothingMovesOnItsOwn:
    def test_there_are_requirements_to_check(self):
        assert len(_requirements()) >= 20

    def test_every_requirement_is_exact(self):
        loose = [
            one
            for one in _requirements()
            if "==" not in one and _name_of(one) not in ALLOWED_LOOSE
        ]
        assert not loose, (
            f"{loose} is not pinned exactly. COMPAT-3 wants an upgrade to be "
            "its own change — add the `==`, or add the name to ALLOWED_LOOSE "
            "with the reason it cannot be."
        )

    def test_the_exceptions_are_real_requirements(self):
        names = {_name_of(one) for one in _requirements()}
        assert set(ALLOWED_LOOSE) <= names, sorted(set(ALLOWED_LOOSE) - names)

    def test_the_lock_file_is_committed(self):
        lock = ROOT / "uv.lock"
        assert lock.exists() and lock.stat().st_size > 10_000


class TestAegraIsADependencyNotAFork:
    def test_it_is_pinned_like_everything_else(self):
        pinned = {
            _name_of(one): one for one in _requirements() if one.startswith("aegra")
        }
        assert {"aegra-api", "aegra-cli"} <= set(pinned), sorted(pinned)
        for one in pinned.values():
            assert "==" in one, one

    def test_the_two_halves_are_the_same_version(self):
        versions = {
            one.split("==")[1]
            for one in _requirements()
            if _name_of(one) in ("aegra-api", "aegra-cli")
        }
        assert len(versions) == 1, versions

    def test_the_server_comes_from_site_packages(self):
        """`import aegra` must resolve to the dependency."""
        import importlib.util

        spec = importlib.util.find_spec("aegra_api")
        assert spec is not None, "aegra_api is not installed; it is a dependency"
        where = Path(spec.origin or (spec.submodule_search_locations or [""])[0])
        assert "site-packages" in where.as_posix(), where

    def test_the_repository_vendors_no_copy_of_it(self):
        for name in ("aegra", "aegra_api", "aegra_cli"):
            assert not (ROOT / name).exists(), (
                f"{name}/ exists at the repository root. COMPAT-1 says do not "
                "fork it — patch at startup instead, the way "
                "`services/agent/aegra/startup.py` does."
            )
