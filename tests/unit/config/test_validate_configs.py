"""Checking a directory of configuration trees against this build."""

from __future__ import annotations

import pytest

from agent.src.agent.config.schema_version import CURRENT, OLDEST_SUPPORTED
from scripts.config.validate_configs import check_trees, main, trees_under


def _tree(root, name, *, version=CURRENT, extra=""):
    tree = root / name
    (tree / "runtime").mkdir(parents=True)
    declared = f"schema_version: {version}\n" if version is not None else ""
    (tree / "runtime" / "agent.yaml").write_text(f'{declared}name: "a"\n{extra}')
    (tree / "PROMPT.md").write_text("You are an agent.\n")
    (tree / "integrations").mkdir()
    (tree / "integrations" / "mcp.json").write_text("{}")
    return tree


class TestFindingTheTrees:
    def test_each_subdirectory_holding_a_tree_is_one(self, tmp_path):
        _tree(tmp_path, "alpha")
        _tree(tmp_path, "beta")
        assert len(trees_under(tmp_path)) == 2

    def test_a_directory_that_is_itself_a_tree_counts(self, tmp_path):
        _tree(tmp_path, "alpha")
        assert len(trees_under(tmp_path / "alpha")) == 1

    def test_a_directory_with_no_tree_in_it_finds_none(self, tmp_path):
        (tmp_path / "notes").mkdir()
        assert trees_under(tmp_path) == []

    def test_the_legacy_flat_layout_is_still_a_tree(self, tmp_path):
        flat = tmp_path / "old"
        flat.mkdir()
        (flat / "agent.yaml").write_text(f"schema_version: {CURRENT}\nname: a\n")
        (flat / "PROMPT.md").write_text("You are an agent.\n")
        (flat / "mcp.json").write_text("{}")
        assert len(trees_under(tmp_path)) == 1


class TestCheckingThem:
    def test_a_good_tree_passes(self, tmp_path):
        _tree(tmp_path, "alpha")
        assert check_trees(tmp_path)[0].ok

    def test_every_tree_is_checked_not_just_until_one_fails(self, tmp_path):
        _tree(tmp_path, "alpha", version=CURRENT + 5)
        _tree(tmp_path, "beta")
        assert len(check_trees(tmp_path)) == 2

    def test_a_tree_this_build_cannot_read_fails(self, tmp_path):
        _tree(tmp_path, "alpha", version=CURRENT + 5)
        assert not check_trees(tmp_path)[0].ok

    def test_the_failure_says_which_version_and_why(self, tmp_path):
        _tree(tmp_path, "alpha", version=CURRENT + 5)
        said = " ".join(check_trees(tmp_path)[0].problems)
        assert str(CURRENT + 5) in said

    def test_a_tree_below_the_window_fails(self, tmp_path):
        _tree(tmp_path, "alpha", version=OLDEST_SUPPORTED - 1)
        assert not check_trees(tmp_path)[0].ok

    def test_a_tree_at_the_old_end_of_the_window_passes(self, tmp_path):
        _tree(tmp_path, "alpha", version=OLDEST_SUPPORTED)
        assert check_trees(tmp_path)[0].ok

    def test_a_tree_with_no_version_passes(self, tmp_path):
        _tree(tmp_path, "alpha", version=None)
        assert check_trees(tmp_path)[0].ok

    def test_a_tree_missing_a_required_file_fails(self, tmp_path):
        tree = _tree(tmp_path, "alpha")
        (tree / "PROMPT.md").unlink()
        assert not check_trees(tmp_path)[0].ok

    def test_the_failure_names_the_file(self, tmp_path):
        tree = _tree(tmp_path, "alpha")
        (tree / "PROMPT.md").unlink()
        said = " ".join(check_trees(tmp_path)[0].problems)
        assert "PROMPT.md" in said

    def test_each_result_names_its_tree(self, tmp_path):
        _tree(tmp_path, "alpha")
        assert check_trees(tmp_path)[0].name == "alpha"


class TestTheExitCode:
    def test_a_clean_directory_exits_zero(self, tmp_path, capsys):
        _tree(tmp_path, "alpha")
        assert main([str(tmp_path)]) == 0

    def test_one_bad_tree_exits_non_zero(self, tmp_path, capsys):
        _tree(tmp_path, "alpha")
        _tree(tmp_path, "beta", version=CURRENT + 5)
        assert main([str(tmp_path)]) != 0

    def test_a_directory_with_no_trees_exits_non_zero(self, tmp_path, capsys):
        (tmp_path / "notes").mkdir()
        assert main([str(tmp_path)]) != 0

    def test_a_missing_directory_is_said_rather_than_crashed(self, tmp_path, capsys):
        assert main([str(tmp_path / "nowhere")]) != 0
        assert "nowhere" in capsys.readouterr().err

    def test_it_prints_a_line_for_every_tree(self, tmp_path, capsys):
        _tree(tmp_path, "alpha")
        _tree(tmp_path, "beta")
        main([str(tmp_path)])
        out = capsys.readouterr().out
        assert "alpha" in out and "beta" in out


class TestTheShippedCorpus:
    """Enough shapes to catch a careless change without reaching"""

    @staticmethod
    def _corpus():
        from pathlib import Path

        return Path(__file__).resolve().parents[2] / "fixtures" / "configs"

    def test_it_exists(self):
        assert self._corpus().is_dir()

    def test_it_holds_several_shapes(
        self,
    ):
        assert len(trees_under(self._corpus())) >= 5

    @pytest.mark.parametrize(
        "shape",
        ["shipped", "minimal", "legacy-flat", "every-block", "oldest-supported"],
    )
    def test_the_shape_is_present(self, shape):
        assert any(t.name == shape for t in trees_under(self._corpus()))

    def test_all_of_them_load(self):
        failed = [r.name for r in check_trees(self._corpus()) if not r.ok]
        assert failed == []
