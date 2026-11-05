"""Measuring how well the corpus answers questions it should."""

from __future__ import annotations

import pytest

from agent.src.knowledge.retrieval_quality import (
    Case,
    measure,
    precision_at,
    recall_at,
)


class TestRecall:
    def test_everything_relevant_found(self):
        assert recall_at(["a", "b"], {"a", "b"}, k=5) == 1.0

    def test_half_found(self):
        assert recall_at(["a", "x"], {"a", "b"}, k=5) == 0.5

    def test_nothing_found(self):
        assert recall_at(["x", "y"], {"a", "b"}, k=5) == 0.0

    def test_only_the_first_k_count(self):
        assert recall_at(["x", "y", "a"], {"a"}, k=2) == 0.0

    def test_a_case_with_nothing_relevant_is_not_counted(self):
        assert recall_at(["x"], set(), k=5) is None


class TestPrecision:
    def test_everything_returned_was_relevant(self):
        assert precision_at(["a", "b"], {"a", "b"}, k=5) == 1.0

    def test_half_was_noise(self):
        assert precision_at(["a", "x"], {"a", "b"}, k=5) == 0.5

    def test_measured_against_what_came_back_not_k(self):
        assert precision_at(["a", "b"], {"a", "b"}, k=5) == 1.0

    def test_nothing_returned_is_not_counted(self):
        assert precision_at([], {"a"}, k=5) is None


class TestMeasuringASetOfCases:
    def _cases(self):
        return [
            Case(query="first", relevant={"d1"}),
            Case(query="second", relevant={"d2"}),
        ]

    def test_a_perfect_searcher_scores_one(self):
        found = measure(lambda q: ["d1"] if q == "first" else ["d2"], self._cases())
        assert found.recall == 1.0
        assert found.precision == 1.0

    def test_a_searcher_that_finds_nothing_scores_zero_recall(self):
        found = measure(lambda q: [], self._cases())
        assert found.recall == 0.0

    def test_a_searcher_that_returns_everything_trades_one_for_the_other(self):
        found = measure(lambda q: ["d1", "d2", "d3", "d4"], self._cases())
        assert found.recall == 1.0
        assert found.precision == pytest.approx(0.25)

    def test_it_says_how_many_cases_it_read(self):
        found = measure(lambda q: ["d1"], self._cases())
        assert found.cases == 2

    def test_a_case_that_returns_nothing_still_counts_against_recall(self):
        found = measure(lambda q: [] if q == "first" else ["d2"], self._cases())
        assert found.recall == 0.5
        assert found.precision == 1.0


class TestItRefusesToMeasureNothing:
    def test_no_cases_at_all_is_an_error(self):
        with pytest.raises(ValueError):
            measure(lambda q: [], [])

    def test_cases_with_no_relevant_documents_are_an_error(self):
        with pytest.raises(ValueError):
            measure(lambda q: [], [Case(query="x", relevant=set())])
