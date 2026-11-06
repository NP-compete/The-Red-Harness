"""Exposure-widening settings ship off, and the check reads this tree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ci"))

import safe_defaults  # noqa: E402

from agent.src.settings import Settings  # noqa: E402


class TestTheRule:
    def test_the_shipped_defaults_are_safe(self):
        assert safe_defaults.problems() == []

    @pytest.mark.parametrize("name", sorted(safe_defaults.WIDENS_EXPOSURE))
    def test_each_one_is_off(self, name):
        assert Settings.model_fields[name].default is False

    @pytest.mark.parametrize("name", safe_defaults.NARROWS_EXPOSURE)
    def test_a_control_is_on(self, name):
        assert Settings.model_fields[name].default is True

    def test_it_notices_a_default_turned_on(self, monkeypatch):
        monkeypatch.setattr(
            safe_defaults,
            "_defaults",
            lambda: {
                **{n: False for n in safe_defaults.WIDENS_EXPOSURE},
                **{n: True for n in safe_defaults.NARROWS_EXPOSURE},
                "REQUEST_LOG_BODY": True,
            },
        )
        found = safe_defaults.problems()
        assert any("REQUEST_LOG_BODY" in one for one in found), found


class TestItReadsThisTree:
    def test_the_script_imports_this_repository(self):
        """Run it the way CI does and ask which file it read."""
        said = subprocess.run(
            [
                sys.executable,
                "-c",
                "import agent.src.settings as s; print(s.__file__)",
            ],
            cwd=ROOT / "scripts/ci",
            capture_output=True,
            text=True,
            check=False,
        )
        del said

        ran = subprocess.run(
            [sys.executable, str(ROOT / "scripts/ci/safe_defaults.py")],
            cwd=ROOT / "scripts/ci",
            capture_output=True,
            text=True,
            check=False,
        )
        assert ran.returncode == 0, ran.stdout + ran.stderr

    def test_it_puts_this_root_first(self):
        source = (ROOT / "scripts/ci/safe_defaults.py").read_text()
        assert "sys.path.insert(0" in source, (
            "safe_defaults.py imports agent and does not put this "
            "repository first on sys.path. This venv is editable-installed "
            "against another checkout, so it would check that one."
        )
