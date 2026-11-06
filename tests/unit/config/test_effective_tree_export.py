"""The whole configuration as it now stands, ready to commit."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agent.src.agent.config.export import effective_tree
from agent.src.agent.config.overlay import InMemoryOverlay
from agent.src.agent.config.resolution import use_overlay

PROMPT = "config/agent/PROMPT.md"


@pytest.fixture(autouse=True)
def _clean():
    use_overlay(None)
    yield
    use_overlay(None)


@pytest.fixture
def tree(tmp_path: Path, monkeypatch) -> Path:
    source = Path(__file__).resolve().parents[3] / "config" / "agent"
    destination = tmp_path / "agent"
    shutil.copytree(source, destination)
    monkeypatch.setenv("CONFIG_PATH", str(destination))
    return destination


class TestItIsComplete:
    def test_every_file_in_the_tree_is_there(self, tree):
        on_disk = {
            f"config/agent/{path.relative_to(tree).as_posix()}"
            for path in tree.rglob("*")
            if path.is_file()
        }
        assert set(effective_tree()) == on_disk

    def test_that_is_more_than_a_handful(self, tree):
        assert len(effective_tree()) >= 5

    def test_the_prompt_is_among_them(self, tree):
        assert PROMPT in effective_tree()


class TestWithNothingEdited:
    def test_every_file_is_byte_identical_to_the_mount(self, tree):
        exported = effective_tree()
        for key, content in exported.items():
            on_disk = tree / key[len("config/agent/") :]
            assert content == on_disk.read_text(), key

    def test_an_empty_overlay_changes_nothing(self, tree):
        before = effective_tree()
        use_overlay(InMemoryOverlay())
        assert effective_tree() == before


class TestWithEdits:
    def test_an_edited_file_exports_what_was_edited(self, tree):
        overlay = InMemoryOverlay()
        overlay.apply(PROMPT, "the new wording\n", author="ada")
        use_overlay(overlay)
        assert effective_tree()[PROMPT] == "the new wording\n"

    def test_everything_else_is_still_the_baseline(self, tree):
        overlay = InMemoryOverlay()
        overlay.apply(PROMPT, "the new wording\n", author="ada")
        use_overlay(overlay)

        exported = effective_tree()
        for key, content in exported.items():
            if key == PROMPT:
                continue
            assert content == (tree / key[len("config/agent/") :]).read_text(), key

    def test_a_file_that_exists_only_as_an_edit_is_included(self, tree):
        added = "config/agent/subagents/invented.md"
        overlay = InMemoryOverlay()
        overlay.apply(added, "# Invented\n", author="ada")
        use_overlay(overlay)
        assert effective_tree()[added] == "# Invented\n"

    def test_an_adopted_baseline_exports_the_baseline(self, tree):
        overlay = InMemoryOverlay()
        overlay.apply(PROMPT, "mine\n", author="ada")
        overlay.adopt_baseline(PROMPT, author="ada")
        use_overlay(overlay)
        assert effective_tree()[PROMPT] == (tree / "PROMPT.md").read_text()


class TestTheLayoutIsTheRepositorys:
    def test_paths_are_relative_and_posix(self, tree):
        for key in effective_tree():
            assert key.startswith("config/agent/")
            assert "\\" not in key
            assert not key.startswith("/")

    def test_nested_files_keep_their_directories(self, tree):
        assert any(key.count("/") >= 3 for key in effective_tree())


class TestTheCheckCanFail:
    def test_an_edit_really_does_show_up(self, tree):
        before = effective_tree()[PROMPT]
        overlay = InMemoryOverlay()
        overlay.apply(PROMPT, "different\n", author="ada")
        use_overlay(overlay)
        assert effective_tree()[PROMPT] != before

    def test_a_file_the_tree_does_not_have_is_not_invented(self, tree):
        assert "config/agent/nothing-like-this.yaml" not in effective_tree()
