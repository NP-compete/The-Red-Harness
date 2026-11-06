"""E22-T2. What a build can honestly say about the eval suite."""

from __future__ import annotations

import json

import pytest

from agent.src.evals.offline import run_offline


class _Config:
    chunk_size = 1200
    chunk_overlap = 200
    top_k = 8
    min_score = 0.35


RETRIEVAL = """\
name: corpus-recall
kind: retrieval
group: retrieval_quality
corpus: agent
decides: blocks a change to chunking
dataset: evals/datasets/d.json
"""

JUDGED = """\
name: safety-one
kind: judged
group: safety
decides: blocks the release
judge: gemini-3.8-flash
dataset: evals/datasets/d.json
cases: [0]
"""


@pytest.fixture
def tree(tmp_path, monkeypatch):
    (tmp_path / "evals" / "checks").mkdir(parents=True)
    (tmp_path / "evals" / "datasets").mkdir(parents=True)
    (tmp_path / "evals" / "datasets" / "d.json").write_text(
        json.dumps({"cases": [{"query": "replay", "relevant": ["doc:a"]}]})
    )
    monkeypatch.setattr("agent.src.data_paths.data_dir", lambda: tmp_path / "data")
    return tmp_path


def _write(tree, name, body):
    (tree / "evals" / "checks" / name).write_text(body)


def _run(tree, found=("doc:a",)):
    return run_offline(
        tree,
        search_for=lambda corpus: lambda q, k: list(found),
        config=_Config(),
        document_ids_for=lambda corpus: list(found),
    )


class TestWhatItRuns:
    def test_a_retrieval_check_is_scored(self, tree):
        _write(tree, "r.yaml", RETRIEVAL)
        report = _run(tree)
        assert [row["name"] for row in report.ran] == ["corpus-recall"]
        assert report.ok

    def test_a_judged_check_is_skipped_with_the_reason(self, tree):
        """Not passed. A build has no model and never will."""
        _write(tree, "j.yaml", JUDGED)
        report = _run(tree)
        assert report.ran == []
        assert report.skipped[0]["name"] == "safety-one"
        assert "no model" in report.skipped[0]["why"]
        assert "gemini-3.8-flash" in report.skipped[0]["why"]

    def test_a_skipped_check_does_not_make_the_build_fail(self, tree):
        _write(tree, "j.yaml", JUDGED)
        assert _run(tree).ok

    def test_nothing_declared_is_said_rather_than_drawn_blank(self, tree):
        assert "nothing is declared" in _run(tree).say()


class TestWhatFailsTheBuild:
    def test_a_dataset_that_is_not_there(self, tree):
        """A check that looks configured and scores nothing makes"""
        _write(tree, "r.yaml", RETRIEVAL.replace("d.json", "missing.json"))
        report = _run(tree)
        assert not report.ok
        assert "does not exist" in report.problems[0]["what"]

    def test_a_check_that_will_not_load(self, tree):
        _write(tree, "bad.yaml", "name: x\ngroup: y\n")
        report = _run(tree)
        assert not report.ok
        assert "decides" in report.problems[0]["what"]

    def test_a_score_that_fell_beyond_the_noise(self, tree):
        _write(tree, "r.yaml", RETRIEVAL)
        assert _run(tree, found=("doc:a",)).ok
        worse = _run(tree, found=("doc:b",))
        assert not worse.ok
        assert worse.regressions[0]["difference"] == -1.0


class TestWhatDoesNot:
    def test_a_first_run(self, tree):
        """There is nothing to compare with, and failing on that"""
        _write(tree, "r.yaml", RETRIEVAL)
        assert _run(tree).ok

    def test_an_improvement(self, tree):
        """A build that fails on the thing somebody was trying to"""
        _write(tree, "r.yaml", RETRIEVAL)
        _run(tree, found=("doc:b",))
        better = _run(tree, found=("doc:a",))
        assert better.ok
        assert better.ran[0]["recall"] == 1.0
