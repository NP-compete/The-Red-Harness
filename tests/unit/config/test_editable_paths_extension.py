"""E25. Widening the editable set without widening it into a file-write."""

from __future__ import annotations

import pytest

from agent.src.agent.config.ui_config_mode import (
    _EDITABLE,
    EXTRA_VARIABLE,
    _extra_paths,
    editable_paths,
)


def test_the_default_set_is_unchanged_without_the_variable(monkeypatch):
    monkeypatch.delenv(EXTRA_VARIABLE, raising=False)
    assert editable_paths() == _EDITABLE


def test_a_deployment_can_add_a_config_path(monkeypatch):
    monkeypatch.setenv(EXTRA_VARIABLE, "config/agent/runtime/pii.yaml")
    paths = editable_paths()
    assert "config/agent/runtime/pii.yaml" in paths
    assert set(_EDITABLE) <= set(paths), "the default set is never lost"


def test_several_paths_and_whitespace(monkeypatch):
    monkeypatch.setenv(
        EXTRA_VARIABLE,
        " config/agent/runtime/pii.yaml , config/agent/runtime/ui.yaml ",
    )
    paths = editable_paths()
    assert "config/agent/runtime/pii.yaml" in paths
    assert "config/agent/runtime/ui.yaml" in paths


def test_a_duplicate_does_not_appear_twice(monkeypatch):
    monkeypatch.setenv(EXTRA_VARIABLE, "config/agent/PROMPT.md")
    assert editable_paths().count("config/agent/PROMPT.md") == 1


@pytest.mark.parametrize(
    "value",
    [
        "/etc/passwd",
        "config/ui/settings.yaml",
        "etc/passwd",
        "../../etc/passwd",
        "config/agent/../../../etc/passwd",
        "services/agent/src/settings.py",
        "",
        "   ",
    ],
)
def test_a_path_that_is_not_configuration_is_refused(value):
    """Outside the config roots, or escaping them, is not an edit."""
    assert _extra_paths(value) == ()


def test_widening_cannot_reach_the_mode(monkeypatch):
    """Read-only must not mean "until somebody posts to it"."""
    monkeypatch.setenv(EXTRA_VARIABLE, "config/agent/UI_CONFIG_MODE")
    widened = editable_paths()

    from agent.src.agent.config import ui_config_mode

    monkeypatch.setenv(ui_config_mode.VARIABLE, "readonly")
    assert ui_config_mode.editing_allowed_now() is False
    assert all(p.startswith("config/agent/") for p in widened)
