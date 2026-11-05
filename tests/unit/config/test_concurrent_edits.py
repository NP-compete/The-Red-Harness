"""E31-T9 / MU-5. Two people with the same config file open."""

from __future__ import annotations

import pytest

from agent.aegra import config_editing_routes as routes
from agent.src.agent.config import resolution
from agent.src.agent.config.overlay import InMemoryOverlay


@pytest.fixture(autouse=True)
def _clean():
    routes.forget_overlay()
    resolution.use_overlay(None)
    yield
    routes.forget_overlay()
    resolution.use_overlay(None)


PATH = "config/agent/PROMPT.md"


def test_an_unedited_file_is_version_zero():
    assert routes._current_version(InMemoryOverlay(), PATH) == 0


def test_no_overlay_is_version_zero():
    """A deployment with no store has one version of everything."""
    assert routes._current_version(None, PATH) == 0


def test_each_edit_moves_the_version():
    overlay = InMemoryOverlay()
    overlay.apply(PATH, "one", author="a")
    assert routes._current_version(overlay, PATH) == 1
    overlay.apply(PATH, "two", author="b")
    assert routes._current_version(overlay, PATH) == 2


def test_adopting_the_baseline_also_moves_it():
    """Going back is a change too: an editor holding the version"""
    overlay = InMemoryOverlay()
    overlay.apply(PATH, "one", author="a")
    overlay.adopt_baseline(PATH, author="a")
    assert routes._current_version(overlay, PATH) == 2


def test_the_version_is_per_path():
    overlay = InMemoryOverlay()
    overlay.apply(PATH, "one", author="a")
    assert routes._current_version(overlay, "config/agent/runtime/agent.yaml") == 0
