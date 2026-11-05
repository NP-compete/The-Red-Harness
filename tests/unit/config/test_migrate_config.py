"""Moving a tree forward one version."""

from __future__ import annotations

import pytest

from agent.src.agent.config.schema_version import CURRENT, OLDEST_SUPPORTED
from scripts.config.migrate_config import Move, migrate


def _tree(tmp_path, *, version=OLDEST_SUPPORTED, body='name: "a"\n', flat=False):
    where = tmp_path if flat else tmp_path / "runtime"
    where.mkdir(parents=True, exist_ok=True)
    declared = f"schema_version: {version}\n" if version is not None else ""
    (where / "agent.yaml").write_text(declared + body)
    return tmp_path


class TestWhatItWrites:
    def test_the_version_goes_up_by_one(self, tmp_path):
        _tree(tmp_path, version=OLDEST_SUPPORTED)
        migrate(tmp_path)
        text = (tmp_path / "runtime" / "agent.yaml").read_text()
        assert f"schema_version: {OLDEST_SUPPORTED + 1}" in text

    def test_a_tree_with_no_version_gets_one(self, tmp_path):
        _tree(tmp_path, version=None)
        migrate(tmp_path)
        text = (tmp_path / "runtime" / "agent.yaml").read_text()
        assert f"schema_version: {OLDEST_SUPPORTED + 1}" in text

    def test_everything_else_is_left_exactly_as_it_was(self, tmp_path):
        body = "# why this name\nname: 'a'   # trailing\n\nmodel: {}\n"
        _tree(tmp_path, body=body)
        migrate(tmp_path)
        after = (tmp_path / "runtime" / "agent.yaml").read_text()
        assert "# why this name" in after
        assert "name: 'a'   # trailing" in after

    def test_it_finds_the_file_on_the_old_layout_too(self, tmp_path):
        _tree(tmp_path, flat=True)
        migrate(tmp_path)
        assert "schema_version" in (tmp_path / "agent.yaml").read_text()


class TestRenames:
    MOVE = Move(frm="old_name", to="new_name", in_section="")

    def test_a_renamed_key_is_rewritten(self, tmp_path):
        _tree(tmp_path, body="old_name: 7\n")
        migrate(tmp_path, moves=(self.MOVE,))
        assert "new_name: 7" in (tmp_path / "runtime" / "agent.yaml").read_text()

    def test_the_old_name_is_gone(self, tmp_path):
        _tree(tmp_path, body="old_name: 7\n")
        migrate(tmp_path, moves=(self.MOVE,))
        assert "old_name" not in (tmp_path / "runtime" / "agent.yaml").read_text()

    def test_the_comment_above_it_stays(self, tmp_path):
        _tree(tmp_path, body="# what this is for\nold_name: 7\n")
        migrate(tmp_path, moves=(self.MOVE,))
        after = (tmp_path / "runtime" / "agent.yaml").read_text()
        assert "# what this is for" in after

    def test_a_key_that_is_not_there_is_not_invented(self, tmp_path):
        _tree(tmp_path, body="name: a\n")
        migrate(tmp_path, moves=(self.MOVE,))
        assert "new_name" not in (tmp_path / "runtime" / "agent.yaml").read_text()

    def test_the_same_word_inside_a_value_is_left_alone(self, tmp_path):
        _tree(tmp_path, body="name: 'the old_name field'\n")
        migrate(tmp_path, moves=(self.MOVE,))
        after = (tmp_path / "runtime" / "agent.yaml").read_text()
        assert "the old_name field" in after


class TestWhatItRefusesToDo:
    def test_a_tree_already_current_is_left_alone(self, tmp_path):
        _tree(tmp_path, version=CURRENT)
        found = migrate(tmp_path)
        assert found.changed == []

    def test_and_says_why(self, tmp_path):
        _tree(tmp_path, version=CURRENT)
        assert "already" in " ".join(migrate(tmp_path).refused).lower()

    def test_a_tree_from_the_future_is_refused(self, tmp_path):
        _tree(tmp_path, version=CURRENT + 1)
        assert migrate(tmp_path).changed == []

    def test_a_tree_with_no_agent_file_is_refused(self, tmp_path):
        assert migrate(tmp_path).refused

    def test_nothing_is_written_when_it_refuses(self, tmp_path):
        _tree(tmp_path, version=CURRENT)
        before = (tmp_path / "runtime" / "agent.yaml").read_text()
        migrate(tmp_path)
        assert (tmp_path / "runtime" / "agent.yaml").read_text() == before


class TestDecisionsItWillNotMakeForYou:
    def test_a_changed_default_is_reported_rather_than_applied(self, tmp_path):
        _tree(tmp_path, body="name: a\n")
        found = migrate(
            tmp_path,
            decisions=("`effects` now defaults to dry_run; set it explicitly.",),
        )
        assert any("dry_run" in note for note in found.decide)

    def test_the_file_still_moves_forward(self, tmp_path):
        _tree(tmp_path, body="name: a\n")
        found = migrate(tmp_path, decisions=("something to decide",))
        assert found.changed


class TestLookingWithoutTouching:
    def test_a_dry_run_writes_nothing(self, tmp_path):
        _tree(tmp_path, body="old_name: 7\n")
        before = (tmp_path / "runtime" / "agent.yaml").read_text()
        migrate(tmp_path, moves=(TestRenames.MOVE,), write=False)
        assert (tmp_path / "runtime" / "agent.yaml").read_text() == before

    def test_a_dry_run_still_says_what_it_would_do(self, tmp_path):
        _tree(tmp_path, body="old_name: 7\n")
        found = migrate(tmp_path, moves=(TestRenames.MOVE,), write=False)
        assert found.changed


class TestTheExitCode:
    def test_a_migrated_tree_exits_zero(self, tmp_path, capsys):
        from scripts.config.migrate_config import main

        _tree(tmp_path)
        assert main([str(tmp_path)]) == 0

    def test_a_refusal_exits_non_zero(self, tmp_path, capsys):
        from scripts.config.migrate_config import main

        _tree(tmp_path, version=CURRENT)
        assert main([str(tmp_path)]) != 0

    def test_a_decision_is_printed_where_it_will_be_read(self, tmp_path, capsys):
        from scripts.config.migrate_config import main

        _tree(tmp_path)
        main([str(tmp_path)])
        assert str(tmp_path) in capsys.readouterr().out

    @pytest.mark.parametrize("flag", ["--dry-run"])
    def test_a_dry_run_is_available_from_the_command_line(self, tmp_path, capsys, flag):
        from scripts.config.migrate_config import main

        _tree(tmp_path)
        before = (tmp_path / "runtime" / "agent.yaml").read_text()
        main([str(tmp_path), flag])
        assert (tmp_path / "runtime" / "agent.yaml").read_text() == before
