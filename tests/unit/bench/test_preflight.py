"""What has to be true before a suite is worth starting (E1-T5)."""

from __future__ import annotations

import pytest

from scripts.bench.preflight import (
    agent_check,
    dataset_check,
    driver_check,
    judge_check,
    preflight,
)


class TestTheDataset:
    def test_an_absent_one_says_where_it_should_be(self):
        found = dataset_check("jb")
        assert not found.ok
        assert "job-bench-eval" in found.detail

    def test_it_points_at_the_pinned_revisions(self):
        assert "PINNED.md" in dataset_check("jb").detail

    def test_a_suite_nobody_has_heard_of_lists_the_ones_there_are(self):
        found = dataset_check("nope")
        assert not found.ok
        assert "jb" in found.detail

    def test_a_populated_directory_passes(self, tmp_path, monkeypatch):
        import scripts.bench.preflight as module

        (tmp_path / "task-1").mkdir()
        monkeypatch.setitem(module.DATASETS, "jb", tmp_path)
        assert dataset_check("jb").ok


class TestTheJudge:
    @pytest.mark.parametrize("name", ["mock-model", "mock", "stub-7b"])
    def test_a_mock_is_refused(self, name):
        found = judge_check(name)
        assert not found.ok
        assert "mock" in found.detail

    def test_no_model_at_all_is_refused_with_the_reason(self):
        found = judge_check("")
        assert not found.ok
        assert "rubric judge" in found.detail

    def test_a_real_model_passes(self):
        assert judge_check("gemini-3.8-flash").ok


class TestTheAgent:
    def test_a_live_agent_is_refused(self):
        found = agent_check("http://localhost:5002", "live")
        assert not found.ok
        assert "dry_run" in found.detail

    def test_an_agent_that_will_not_say_is_refused(self):
        assert not agent_check("http://localhost:5002", "").ok

    def test_dry_run_passes(self):
        assert agent_check("http://localhost:5002", "dry_run").ok


class TestItDoesNotClaimToBeReady:
    def test_the_driver_is_reported_missing(self):
        assert not driver_check().ok

    def test_every_prerequisite_comes_back_in_one_call(self):
        found = preflight(
            suite="jb", url="http://x", effects="dry_run", model="mock-model"
        )
        assert [one.name for one in found] == [
            "agent",
            "dataset",
            "judge model",
            "suite driver",
        ]
