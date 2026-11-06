"""The engine that scores a declared check against a running agent."""

from __future__ import annotations

import json

import pytest

from agent.src.evals.live import (
    Case,
    load_cases,
    read_verdict,
    rubric_for,
    run_case,
    verdict_prompt,
)
from agent.src.evals.registry import Check


def _dataset(tmp_path, evals):
    path = tmp_path / "evals" / "datasets" / "cases.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"evals": evals}), encoding="utf-8")
    return tmp_path


def _check(**kwargs):
    return Check(
        name="a-check",
        group="accuracy",
        decides="blocks the release",
        judge="a-judge",
        dataset="evals/datasets/cases.json",
        **kwargs,
    )


CASE = {"id": 1, "prompt": "ask me", "assertions": ["says yes", "does not shout"]}


class TestLoadingCases:
    def test_reads_only_the_cases_the_check_names(self, tmp_path):
        root = _dataset(tmp_path, [CASE, {**CASE, "id": 2}])
        cases = load_cases(root, _check(cases=(2,)))
        assert [c.id for c in cases] == [2]

    def test_a_named_case_that_is_missing_is_an_error(self, tmp_path):
        root = _dataset(tmp_path, [CASE])
        with pytest.raises(ValueError, match="no case 4"):
            load_cases(root, _check(cases=(4,)))

    def test_a_case_that_asserts_nothing_is_an_error(self, tmp_path):
        root = _dataset(tmp_path, [{"id": 1, "prompt": "p", "assertions": []}])
        with pytest.raises(ValueError, match="asserts nothing"):
            load_cases(root, _check())


class TestTheRubric:
    def test_every_assertion_is_required(self):
        rubric = rubric_for(Case(id=1, prompt="p", assertions=("a", "b")))
        assert all(c.required for c in rubric.criteria)
        assert rubric.pass_mark == 1.0

    def test_the_judge_is_asked_by_number_not_by_wording(self):
        asked = verdict_prompt(Case(id=1, prompt="p", assertions=("a", "b")), "reply")
        assert "1. a" in asked and "2. b" in asked


class TestReadingTheVerdict:
    RUBRIC = rubric_for(Case(id=1, prompt="p", assertions=("a", "b")))

    def test_reads_a_fenced_object(self):
        got = read_verdict('```json\n{"1": true, "2": false}\n```', self.RUBRIC)
        assert got == {"1": True, "2": False}

    def test_reads_an_object_with_chatter_around_it(self):
        got = read_verdict(
            'Sure! {"1": true, "2": true} — hope that helps', self.RUBRIC
        )
        assert got == {"1": True, "2": True}

    def test_drops_a_key_the_rubric_did_not_ask_about(self):
        assert read_verdict('{"1": true, "9": true}', self.RUBRIC) == {"1": True}

    def test_unreadable_is_empty_rather_than_an_exception(self):
        assert read_verdict("I could not say", self.RUBRIC) == {}


class TestScoringACase:
    CASE = Case(id=1, prompt="ask me", assertions=("says yes", "does not shout"))

    def test_all_assertions_met_is_a_pass(self):
        scored = run_case(
            self.CASE, ask=lambda _: "yes", judge=lambda _: '{"1": true, "2": true}'
        )
        assert scored.judgement.passed
        assert "passed 2 assertion(s)" in scored.say()

    def test_one_assertion_unmet_fails_and_names_it(self):
        scored = run_case(
            self.CASE, ask=lambda _: "YES", judge=lambda _: '{"1": true, "2": false}'
        )
        assert not scored.judgement.passed
        assert "does not shout" in scored.say()

    def test_an_unreadable_verdict_is_not_scored_rather_than_failed(self):
        scored = run_case(self.CASE, ask=lambda _: "yes", judge=lambda _: "dunno")
        assert not scored.judgement.reliable
        assert not scored.judgement.passed
        assert "not scored" in scored.say()
