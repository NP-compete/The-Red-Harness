"""`docs/development/unreachable.md` may not name a file that is gone."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "development" / "unreachable.md"
TEXT = PAGE.read_text()

PATHS = sorted(
    {found for found in re.findall(r"`([a-z_][\w/]*\.py)`", TEXT) if "/" in found}
)


class TestNoDeadPaths:
    def test_the_page_was_read(self):
        assert "reached by nothing" in TEXT
        assert len(TEXT) > 2000

    @pytest.mark.parametrize("path", PATHS or ["(none)"])
    def test_every_path_it_names_exists(self, path: str):
        if path == "(none)":
            return
        for base in (ROOT / "services" / "agent", ROOT):
            if (base / path).exists():
                return
        raise AssertionError(
            f"docs/development/unreachable.md names `{path}` and no such file exists. "
            "The page describes what a test computes — it must not drift "
            "into listing files that are gone."
        )


class TestItDoesNotCopyTheAnswerBack:
    def test_there_is_no_hand_written_list(self):
        bullets = re.findall(r"^- `[\w/]+\.py`$", TEXT, re.M)
        assert not bullets, (
            f"{len(bullets)} module paths are listed by hand again. "
            "`make unreachable` prints the live list; a copy of it here is "
            "wrong the first time somebody deletes one."
        )

    def test_it_points_at_the_command_and_the_ratchet(self):
        assert "make unreachable" in TEXT
        assert "test_unreachable_modules.py" in TEXT

    def test_it_does_not_restate_the_total(self):
        claims = re.findall(r"there are \*\*\d+\*\* of them", TEXT)
        assert not claims, claims
