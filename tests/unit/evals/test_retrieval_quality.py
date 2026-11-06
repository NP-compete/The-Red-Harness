"""E35-T4. Measuring whether retrieval finds the right documents."""

from __future__ import annotations

import pytest

from agent.src.evals.retrieval_quality import (
    Case,
    as_result,
    measure,
    read_cases,
)


def _fixed(answers: dict[str, list[str]]):
    def _search(query: str, k: int) -> list[str]:
        return answers.get(query, [])[:k]

    return _search


class TestScoring:
    def test_a_perfect_corpus_scores_one(self):
        found = measure(
            [Case("a", ("d1",))], search=_fixed({"a": ["d1"]}), corpus="agent"
        )
        assert found.recall == 1.0
        assert found.precision == 1.0

    def test_a_missed_document_is_named(self):
        """A list of ids sends somebody to three files; "recall"""
        found = measure(
            [Case("a", ("d1", "d2"))], search=_fixed({"a": ["d1"]}), corpus="agent"
        )
        assert found.recall == 0.5
        assert found.cases[0].missed == ("d2",)

    def test_precision_is_over_what_came_back_not_over_k(self):
        """Scoring 1/8 would punish a small corpus for being small."""
        found = measure(
            [Case("a", ("d1",))],
            search=_fixed({"a": ["d1", "junk"]}),
            corpus="agent",
            k=8,
        )
        assert found.precision == 0.5

    def test_nothing_found_is_zero_rather_than_an_error(self):
        found = measure([Case("a", ("d1",))], search=_fixed({}), corpus="agent")
        assert found.recall == 0.0
        assert found.precision == 0.0

    def test_only_the_first_k_are_scored(self):
        """Scoring ten when the agent is shown eight measures"""
        found = measure(
            [Case("a", ("d9",))],
            search=lambda q, k: [f"d{i}" for i in range(1, 10)][:k],
            corpus="agent",
            k=3,
        )
        assert found.recall == 0.0

    def test_the_worst_case_comes_first(self):
        found = measure(
            [Case("a", ("d1",)), Case("b", ("d2",))],
            search=_fixed({"a": ["d1"]}),
            corpus="agent",
        )
        assert found.worst[0].query == "b"


class TestWhatItRefuses:
    def test_a_case_with_no_right_answer(self):
        with pytest.raises(ValueError, match="neither pass nor fail"):
            Case("a", ())

    def test_a_case_with_no_query(self):
        with pytest.raises(ValueError, match="needs a query"):
            Case("  ", ("d1",))

    def test_a_measurement_over_no_cases(self):
        with pytest.raises(ValueError, match="not a measurement"):
            measure([], search=_fixed({}), corpus="agent")

    def test_scoring_over_no_documents(self):
        with pytest.raises(ValueError, match="not scored"):
            measure([Case("a", ("d1",))], search=_fixed({}), corpus="agent", k=0)

    def test_a_dataset_that_is_not_a_list(self):
        with pytest.raises(ValueError, match="list of cases"):
            read_cases({"query": "a"})


class TestFeedingTheGate:
    def test_the_suite_name_carries_the_corpus(self):
        """Two corpora compared against each other is a comparison"""
        found = measure(
            [Case("a", ("d1",))], search=_fixed({"a": ["d1"]}), corpus="handbook"
        )
        assert as_result(found, fingerprint="abc").suite == "retrieval:handbook"

    def test_recall_is_the_score_the_gate_sees(self):
        found = measure(
            [Case("a", ("d1", "d2"))], search=_fixed({"a": ["d1"]}), corpus="agent"
        )
        assert as_result(found, fingerprint="abc").score == 0.5

    def test_the_variance_travels_with_it(self):
        """`ResultsStore.compare` uses it as the noise floor: a"""
        found = measure(
            [Case("a", ("d1",)), Case("b", ("d2",))],
            search=_fixed({"a": ["d1"]}),
            corpus="agent",
        )
        assert as_result(found, fingerprint="abc").variance == 0.25

    def test_a_result_needs_the_configuration_that_earned_it(self):
        found = measure(
            [Case("a", ("d1",))], search=_fixed({"a": ["d1"]}), corpus="agent"
        )
        with pytest.raises(ValueError, match="must name the configuration"):
            as_result(found, fingerprint="   ")
