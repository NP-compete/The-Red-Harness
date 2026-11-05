"""Reading a config file, with any edit laid over it."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.src.agent.config.overlay import InMemoryOverlay
from agent.src.agent.config.resolution import (
    effective_text,
    overlay_key,
    use_overlay,
)


@pytest.fixture(autouse=True)
def _no_overlay():
    """No overlay unless a test asks for one."""
    use_overlay(None)
    yield
    use_overlay(None)


@pytest.fixture
def a_file(tmp_path: Path) -> Path:
    path = tmp_path / "agent.yaml"
    path.write_text("name: tracker\n  trailing:   spaces   \n\n")
    return path


class TestWithNoOverlay:
    def test_it_reads_the_file(self, a_file):
        assert effective_text(a_file) == a_file.read_text()

    def test_byte_for_byte(self, a_file):
        assert effective_text(a_file) == "name: tracker\n  trailing:   spaces   \n\n"

    def test_a_missing_file_raises_as_it_would_have(self, tmp_path):
        with pytest.raises(OSError):
            effective_text(tmp_path / "absent.yaml")


class TestWithAnOverlayThatSaysNothing:
    def test_the_file_still_wins(self, a_file):
        use_overlay(InMemoryOverlay())
        assert effective_text(a_file) == a_file.read_text()

    def test_an_overlay_for_a_different_path_is_ignored(self, a_file):
        overlay = InMemoryOverlay()
        overlay.apply("config/agent/runtime/router.yaml", "elsewhere", author="ada")
        use_overlay(overlay)
        assert effective_text(a_file) == a_file.read_text()


class TestWithAnOverlayForThisPath:
    def test_the_overlay_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
        path = tmp_path / "runtime" / "agent.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("name: from-the-mount\n")

        overlay = InMemoryOverlay()
        overlay.apply(overlay_key(path), "name: from-the-overlay\n", author="ada")
        use_overlay(overlay)

        assert effective_text(path) == "name: from-the-overlay\n"

    def test_adopting_the_baseline_gives_the_file_back(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
        path = tmp_path / "runtime" / "agent.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("name: from-the-mount\n")

        overlay = InMemoryOverlay()
        key = overlay_key(path)
        overlay.apply(key, "name: mine\n", author="ada")
        overlay.adopt_baseline(key, author="ada")
        use_overlay(overlay)

        assert effective_text(path) == "name: from-the-mount\n"

    def test_an_overlay_can_stand_in_for_a_file_that_is_not_there(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
        path = tmp_path / "runtime" / "new.yaml"
        overlay = InMemoryOverlay()
        overlay.apply(overlay_key(path), "name: invented\n", author="ada")
        use_overlay(overlay)

        assert effective_text(path) == "name: invented\n"


class TestTheKeyIsStable:
    def test_it_does_not_depend_on_where_the_tree_is_mounted(
        self, monkeypatch, tmp_path
    ):
        here = tmp_path / "one"
        there = tmp_path / "two"
        for root in (here, there):
            (root / "runtime").mkdir(parents=True)

        monkeypatch.setenv("CONFIG_PATH", str(here))
        first = overlay_key(here / "runtime" / "agent.yaml")
        monkeypatch.setenv("CONFIG_PATH", str(there))
        second = overlay_key(there / "runtime" / "agent.yaml")

        assert first == second

    def test_it_reads_like_the_path_somebody_would_type(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
        assert overlay_key(tmp_path / "runtime" / "agent.yaml") == (
            "config/agent/runtime/agent.yaml"
        )

    def test_a_path_outside_the_tree_has_no_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path / "config"))
        assert overlay_key(Path("/etc/passwd")) is None

    def test_a_path_that_climbs_out_has_no_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path / "config"))
        assert overlay_key(tmp_path / "config" / ".." / "secrets.yaml") is None


class TestTheCheckCanFail:
    def test_an_overlay_really_does_change_the_answer(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
        path = tmp_path / "runtime" / "agent.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("baseline\n")

        before = effective_text(path)
        overlay = InMemoryOverlay()
        overlay.apply(overlay_key(path), "overlaid\n", author="ada")
        use_overlay(overlay)

        assert before == "baseline\n"
        assert effective_text(path) == "overlaid\n"
