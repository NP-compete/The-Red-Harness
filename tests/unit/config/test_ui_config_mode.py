"""Whether this deployment may be reconfigured from a browser."""

from __future__ import annotations

import pytest

from agent.src.agent.config.ui_config_mode import (
    MODES,
    editing_allowed,
    mode_from,
)


class TestTheDefault:
    def test_nothing_set_is_read_only(self):
        assert mode_from(None) == "readonly"
        assert not editing_allowed(None)

    def test_an_empty_value_is_read_only(self):
        assert not editing_allowed("")

    def test_whitespace_is_read_only(self):
        assert not editing_allowed("   ")


class TestTurningItOn:
    def test_readwrite_allows_editing(self):
        assert editing_allowed("readwrite")

    def test_it_is_not_case_sensitive(self):
        assert editing_allowed("ReadWrite")
        assert editing_allowed("READWRITE")

    def test_surrounding_whitespace_does_not_matter(self):
        assert editing_allowed("  readwrite  ")


class TestAnythingElseIsReadOnly:
    @pytest.mark.parametrize(
        "unrecognised",
        ["readwrit", "read-write", "rw", "true", "1", "yes", "writable", "admin"],
    )
    def test_a_value_that_is_not_a_mode_does_not_permit_writing(self, unrecognised):
        assert not editing_allowed(unrecognised)

    def test_the_mode_reported_for_an_unrecognised_value_is_readonly(self):
        assert mode_from("rw") == "readonly"


class TestThereAreExactlyTwoModes:
    def test_the_pair_is_the_whole_set(self):
        assert MODES == ("readonly", "readwrite")

    def test_every_mode_has_a_decided_answer(self):
        for mode in MODES:
            assert editing_allowed(mode) in (True, False)

    def test_exactly_one_of_them_permits_writing(self):
        assert [editing_allowed(mode) for mode in MODES].count(True) == 1


class TestItIsReadFromTheEnvironment:
    def test_the_environment_decides(self, monkeypatch):
        from agent.src.agent.config import ui_config_mode

        monkeypatch.setenv("UI_CONFIG_MODE", "readwrite")
        assert ui_config_mode.editing_allowed_now()

    def test_absent_from_the_environment_is_read_only(self, monkeypatch):
        from agent.src.agent.config import ui_config_mode

        monkeypatch.delenv("UI_CONFIG_MODE", raising=False)
        assert not ui_config_mode.editing_allowed_now()

    def test_it_is_read_each_time_rather_than_held(self, monkeypatch):
        from agent.src.agent.config import ui_config_mode

        monkeypatch.setenv("UI_CONFIG_MODE", "readwrite")
        assert ui_config_mode.editing_allowed_now()
        monkeypatch.setenv("UI_CONFIG_MODE", "readonly")
        assert not ui_config_mode.editing_allowed_now()


class TestTheSettingIsNotItselfEditable:
    def test_it_is_not_among_the_editable_paths(self):
        from agent.src.agent.config.ui_config_mode import editable_paths

        for path in editable_paths():
            assert "ui_config_mode" not in path
            assert "UI_CONFIG_MODE" not in path

    def test_the_editable_paths_are_worth_having(self):
        from agent.src.agent.config.ui_config_mode import editable_paths

        assert len(editable_paths()) >= 5
