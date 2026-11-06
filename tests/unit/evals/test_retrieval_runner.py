"""E22-T3. A retrieval check's score is kept, and compared."""

from __future__ import annotations

import json

import pytest

from agent.src.evals import usage
from agent.src.evals.registry import Check, CheckRegistry
from agent.src.evals.retrieval_runner import (
    cases_for,
    retrieval_fingerprint,
    run_check,
)


class _Config:
    chunk_size = 1200
    chunk_overlap = 200
    top_k = 8
    min_score = 0.35


@pytest.fixture
def tree(tmp_path, monkeypatch):
    (tmp_path / "evals" / "datasets").mkdir(parents=True)
    (tmp_path / "evals" / "datasets" / "d.json").write_text(
        json.dumps(
            {
                "cases": [
                    {"query": "replay", "relevant": ["doc:a"]},
                    {"query": "receipts", "relevant": ["doc:b"]},
                ]
            }
        )
    )
    monkeypatch.setattr("agent.src.data_paths.data_dir", lambda: tmp_path / "data")
    return tmp_path


def _check(**over):
    fields = {
        "name": "corpus-recall",
        "group": "retrieval_quality",
        "decides": "blocks a change to chunking",
        "kind": "retrieval",
        "corpus": "agent",
        "dataset": "evals/datasets/d.json",
    }
    fields.update(over)
    return Check(**fields)


class TestTheFingerprint:
    def test_the_same_configuration_scores_under_the_same_name(self):
        first = retrieval_fingerprint(_Config(), ["doc:a"])
        assert first == retrieval_fingerprint(_Config(), ["doc:a"])

    def test_changing_the_chunking_changes_it(self):
        class _Other(_Config):
            chunk_size = 600

        assert retrieval_fingerprint(_Config(), ["doc:a"]) != retrieval_fingerprint(
            _Other(), ["doc:a"]
        )

    def test_changing_the_corpus_changes_it(self):
        """Re-ingesting *should* invalidate the comparison: a"""
        assert retrieval_fingerprint(_Config(), ["doc:a"]) != retrieval_fingerprint(
            _Config(), ["doc:a", "doc:b"]
        )

    def test_the_order_documents_arrive_in_does_not(self):
        assert retrieval_fingerprint(_Config(), ["b", "a"]) == retrieval_fingerprint(
            _Config(), ["a", "b"]
        )

    def test_it_is_short_enough_to_read(self):
        """It appears in a log line and a diff; a 64-character hash"""
        assert len(retrieval_fingerprint(_Config(), [])) == 12


class TestRunningIt:
    def test_a_first_run_has_nothing_to_compare_with(self, tree):
        """And says so: "no regression" would read as a comparison"""
        _, comparison = run_check(
            _check(),
            root=tree,
            search=lambda q, k: ["doc:a", "doc:b"],
            config=_Config(),
            document_ids=["doc:a", "doc:b"],
        )
        assert comparison is None

    def test_a_worse_configuration_is_a_significant_difference(self, tree):
        run_check(
            _check(),
            root=tree,
            search=lambda q, k: ["doc:a", "doc:b"],
            config=_Config(),
            document_ids=["doc:a", "doc:b"],
        )
        measured, comparison = run_check(
            _check(),
            root=tree,
            search=lambda q, k: ["doc:a"],
            config=_Config(),
            document_ids=["doc:a"],
        )
        assert measured.recall == 0.5
        assert comparison.difference == -0.5
        assert comparison.significant

    def test_running_it_is_counted_on_disk(self, tree):
        """The registry is rebuilt per request, so a count that"""
        registry = CheckRegistry([_check()])
        run_check(
            _check(),
            root=tree,
            search=lambda q, k: ["doc:a"],
            config=_Config(),
            document_ids=["doc:a"],
            registry=registry,
        )
        assert usage.applied_to(registry) == {"corpus-recall": 1}


class TestTheCases:
    def test_a_check_with_no_dataset_is_refused(self, tree):
        with pytest.raises(ValueError, match="names no dataset"):
            cases_for(_check(dataset=""), tree)

    def test_a_dataset_that_is_not_there_is_refused(self, tree):
        with pytest.raises(ValueError, match="does not exist"):
            cases_for(_check(dataset="evals/datasets/missing.json"), tree)

    def test_a_check_may_name_the_cases_it_is_about(self, tree):
        assert len(cases_for(_check(cases=(1,)), tree)) == 1

    def test_naming_a_case_the_dataset_does_not_have_is_refused(self, tree):
        with pytest.raises(ValueError, match="names case 7"):
            cases_for(_check(cases=(7,)), tree)
