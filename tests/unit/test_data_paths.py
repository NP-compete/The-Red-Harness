"""Where the agent keeps its files when the container path is not there."""

from __future__ import annotations

from pathlib import Path

from agent.src.data_paths import writable_dir


def test_uses_the_configured_path_when_it_can_be_made(tmp_path: Path):
    wanted = tmp_path / "data"
    assert writable_dir(str(wanted), "data") == wanted
    assert wanted.is_dir()


def test_uses_a_path_that_already_exists(tmp_path: Path):
    wanted = tmp_path / "data"
    wanted.mkdir()
    assert writable_dir(str(wanted), "data") == wanted


def test_falls_back_when_the_path_cannot_be_made(tmp_path: Path, monkeypatch):
    """A container path like /app/data does not exist on a laptop."""
    monkeypatch.setattr("agent.src.data_paths._LOCAL_ROOT", tmp_path / ".local")
    found = writable_dir("/app/data", "data")
    assert found == tmp_path / ".local" / "data"
    assert found.is_dir()


def test_the_fallback_is_named_after_what_it_holds(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("agent.src.data_paths._LOCAL_ROOT", tmp_path / ".local")
    assert writable_dir("/app/data/documents", "documents").name == "documents"


def test_an_empty_setting_still_lands_somewhere_writable(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("agent.src.data_paths._LOCAL_ROOT", tmp_path / ".local")
    assert writable_dir("", "data") == tmp_path / ".local" / "data"


def test_a_file_in_the_way_is_not_treated_as_a_directory(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("agent.src.data_paths._LOCAL_ROOT", tmp_path / ".local")
    blocked = tmp_path / "taken"
    blocked.write_text("not a directory")
    assert writable_dir(str(blocked), "data") == tmp_path / ".local" / "data"
