"""A declared flag reaches the capability it names (CFG-1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ci"))

import capability_gates as gates  # noqa: E402


class TestTheShippedRegistry:
    def test_it_passes(self):
        assert gates.problems() == []

    def test_every_excused_flag_is_in_the_registry(self):
        declared = set(gates.declared())
        excused = set(gates.RESERVED) | set(gates.UNGATED)
        assert excused <= declared, sorted(excused - declared)

    def test_the_two_lists_do_not_overlap(self):
        assert not (set(gates.RESERVED) & set(gates.UNGATED))

    def test_every_flag_is_accounted_for(self):
        for flag in gates.declared():
            assert (
                gates.readers(flag) or flag in gates.RESERVED or flag in gates.UNGATED
            ), flag


class TestItCanFail:
    def test_a_flag_nobody_reads_and_nobody_excused(self, monkeypatch):
        monkeypatch.setattr(
            gates,
            "declared",
            lambda: {**{k: {} for k in gates.RESERVED}, "invented_enabled": {}},
        )
        monkeypatch.setattr(gates, "UNGATED", {})
        found = gates.problems()
        assert any("invented_enabled" in one for one in found), found

    def test_an_exemption_that_is_no_longer_true(self, monkeypatch):
        """The capability got its gate and the exemption stayed."""
        monkeypatch.setattr(gates, "readers", lambda flag: ["services/agent/thing.py"])
        found = gates.problems()
        assert any("planner_enabled" in one for one in found), found
        assert any("capability is gated now" in one for one in found), found

    def test_an_exemption_for_a_flag_that_was_removed(self, monkeypatch):
        monkeypatch.setattr(gates, "RESERVED", {"gone_enabled": "a reason"})
        monkeypatch.setattr(gates, "UNGATED", {})
        found = gates.problems()
        assert any("gone_enabled" in one for one in found), found


class TestNothingIsUngated:
    """`UNGATED` is empty, and kept so the next one has a home."""

    def test_it_is_empty(self):
        assert gates.UNGATED == {}, (
            f"{sorted(gates.UNGATED)} are built, declared and ungated. Each "
            "is a switch wired to nothing."
        )

    def test_the_reasoning_flag_now_reaches_code(self):
        who = gates.readers("reasoning_profiles_enabled")
        assert who, "the user-scoped gate is gone again"

    @pytest.mark.parametrize("flag", sorted(gates.UNGATED))
    def test_a_reason_says_what_is_in_the_way(self, flag):
        assert len(gates.UNGATED[flag]) > 40
