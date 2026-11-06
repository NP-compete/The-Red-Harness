"""Problems found while loading, kept where somebody can see them."""

from __future__ import annotations

import pytest

from agent.src.agent.config.problems import (
    found_problems,
    note_problem,
    reset_problems,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_problems()
    yield
    reset_problems()


class TestRemembering:
    def test_a_clean_load_has_nothing_to_report(self):
        assert found_problems() == []

    def test_a_problem_is_remembered(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        assert len(found_problems()) == 1

    def test_it_remembers_which_file(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        assert found_problems()[0].source == "runtime/agent.yaml"

    def test_it_remembers_what_was_wrong(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        assert "duplicate key" in found_problems()[0].detail

    def test_several_are_all_kept(self):
        note_problem("a.yaml", "one")
        note_problem("b.yaml", "two")
        assert len(found_problems()) == 2


class TestNotGrowingWithoutBound:
    """Config is re-read on a reload, and a problem recurs each time."""

    def test_the_same_problem_is_recorded_once(self):
        for _ in range(5):
            note_problem("runtime/agent.yaml", "duplicate key 'model'")
        assert len(found_problems()) == 1

    def test_a_different_problem_in_the_same_file_is_its_own(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        note_problem("runtime/agent.yaml", "duplicate key 'tools'")
        assert len(found_problems()) == 2

    def test_a_reload_that_fixed_it_clears_the_old_one(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        reset_problems()
        assert found_problems() == []


class TestWhatIsReported:
    def test_it_is_safe_to_show_an_operator(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model' at line 4")
        said = found_problems()[0]
        assert said.detail == "duplicate key 'model' at line 4"

    def test_the_shape_is_stable(self):
        note_problem("a.yaml", "one")
        found = found_problems()[0]
        assert hasattr(found, "source") and hasattr(found, "detail")


class TestTheLoaderRecordsWhatItFinds:
    """A duplicate key reaches the registry, not only the log."""

    @staticmethod
    def _load(tmp_path, text, monkeypatch):
        from agent.src.agent.config.loader import agent_config

        tree = tmp_path / "runtime"
        tree.mkdir()
        (tree / "agent.yaml").write_text(text)
        monkeypatch.setattr(agent_config, "_base_dir", tmp_path)
        agent_config._load_agent_yaml()

    def test_a_duplicate_key_is_remembered(self, tmp_path, monkeypatch):
        self._load(tmp_path, "model: a\nmodel: b\n", monkeypatch)
        assert any("model" in p.detail for p in found_problems())

    def test_it_names_the_file_it_was_in(self, tmp_path, monkeypatch):
        self._load(tmp_path, "model: a\nmodel: b\n", monkeypatch)
        assert any("agent.yaml" in p.source for p in found_problems())

    def test_a_file_with_no_duplicates_records_none(self, tmp_path, monkeypatch):
        self._load(tmp_path, "schema_version: 3\nmodel: a\n", monkeypatch)
        assert [p for p in found_problems() if "duplicate" in p.detail] == []
