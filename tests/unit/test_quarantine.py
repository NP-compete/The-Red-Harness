"""The flake quarantine, and its expiry (E26-T11)."""

from __future__ import annotations

from datetime import date

import pytest

from tests.quarantine import (
    QUARANTINE,
    QuarantineInvalid,
    expired,
    load,
    read_quarantine,
)

ONE = """
quarantined:
  - test: tests/unit/foo/test_bar.py::TestBaz::test_sometimes
    owner: ada
    until: 2026-11-30
    reason: races with the Redis fixture
"""


class TestWhatCountsAsAnEntry:
    def test_a_full_entry_is_read(self):
        found = read_quarantine(ONE)
        assert found[0].owner == "ada"
        assert found[0].until == date(2026, 11, 30)

    @pytest.mark.parametrize("missing", ["owner", "until"])
    def test_an_entry_without_an_owner_or_a_date_is_refused(self, missing):
        text = "\n".join(line for line in ONE.splitlines() if f"{missing}:" not in line)
        with pytest.raises(QuarantineInvalid, match=missing):
            read_quarantine(text)

    def test_a_pattern_is_refused(self):
        with pytest.raises(QuarantineInvalid, match="not one test"):
            read_quarantine(
                "quarantined:\n  - test: tests/unit/*\n    owner: ada\n"
                "    until: 2026-11-30\n"
            )

    def test_so_is_a_bare_file(self):
        with pytest.raises(QuarantineInvalid, match="not one test"):
            read_quarantine(
                "quarantined:\n  - test: tests/unit/test_x.py\n    owner: ada\n"
                "    until: 2026-11-30\n"
            )

    def test_a_date_that_is_not_a_date_is_refused(self):
        with pytest.raises(QuarantineInvalid, match="must be a date"):
            read_quarantine(
                "quarantined:\n  - test: a.py::b\n    owner: ada\n    until: soon\n"
            )

    def test_an_absent_file_is_an_empty_quarantine(self, tmp_path):
        assert load(tmp_path / "nothing.yaml") == []


class TestExpiry:
    def test_an_entry_past_its_date_has_expired(self):
        found = read_quarantine(ONE)
        assert expired(found, date(2026, 12, 1))

    def test_one_still_in_date_has_not(self):
        found = read_quarantine(ONE)
        assert not expired(found, date(2026, 11, 1))


class TestTheRealFile:
    def test_it_parses(self):
        load()

    def test_nothing_in_it_has_expired(self):
        overdue = expired(load())
        assert not overdue, "expired quarantine entries: " + ", ".join(
            f"{one.test} (owner {one.owner}, due {one.until})" for one in overdue
        )

    def test_the_file_is_where_the_hook_looks(self):
        assert QUARANTINE.name == "quarantine.yaml"
