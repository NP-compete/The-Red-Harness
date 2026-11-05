"""The checks, from a terminal (E28-T8)."""

from __future__ import annotations

import pytest

from agent.cli.evals import (
    EvalFailed,
    NotScorable,
    Usage,
    checks,
    score,
    usage,
    why_unused,
)


class _Transport:
    def __init__(self, answers):
        self.answers = answers

    def get(self, path: str):
        for key, answer in self.answers.items():
            if key in path:
                return answer
        return 404, {"message": "no such route"}

    def post(self, path: str, body=None):
        for key, answer in self.answers.items():
            if key in path:
                return answer
        return 404, {"message": "no such route"}


CHECKS = (
    200,
    {
        "groups": ["accuracy"],
        "checks": [
            {
                "name": "no-invented-observability",
                "group": "accuracy",
                "decides": "blocks the incident-triage skill",
                "judge": "gemini-3.8-flash",
            }
        ],
    },
)


class TestTheList:
    def test_it_names_the_group_and_the_judge(self):
        found = checks(transport=_Transport({"/evals/checks": CHECKS}))
        assert found[0].group == "accuracy"
        assert found[0].judge == "gemini-3.8-flash"

    def test_a_refusal_is_not_an_empty_list(self):
        with pytest.raises(EvalFailed):
            checks(transport=_Transport({}))


class TestWhatAZeroMeans:
    def test_nothing_having_run_is_said_to_be_no_evidence(self):
        found = Usage(rows=[("a", 0), ("b", 0)], unused=["a", "b"])
        assert "say nothing" in why_unused(found)

    def test_a_deployment_that_does_run_them_gets_the_other_sentence(self):
        found = Usage(rows=[("a", 7), ("b", 0)], unused=["b"])
        assert "evidence" in why_unused(found)

    def test_nothing_unused_needs_no_sentence(self):
        assert why_unused(Usage(rows=[("a", 1)], unused=[])) == ""

    def test_the_rows_come_back_as_counts(self):
        transport = _Transport(
            {"/usage": (200, {"rows": [{"name": "a", "runs": 3}], "unused": []})}
        )
        assert usage(transport=transport).rows == [("a", 3)]


class TestRunningOne:
    def test_a_score_comes_back_whole(self):
        transport = _Transport({"/v1/eval/retrieval": (200, {"recall": 1.0})})
        assert score("corpus-recall", transport=transport)["recall"] == 1.0

    def test_a_check_with_nothing_to_score_is_refused_not_zeroed(self):
        transport = _Transport(
            {"/v1/eval/retrieval": (404, {"message": "no document library"})}
        )
        with pytest.raises(NotScorable, match="no document library"):
            score("corpus-recall", transport=transport)

    def test_an_unscorable_check_is_its_own_kind_of_failure(self):
        assert issubclass(NotScorable, EvalFailed)


class TestTheKindIsReadNotInferred:
    """The route dropped it, so a client had to guess."""

    def _one(self, extra):
        payload = (
            200,
            {"groups": ["g"], "checks": [{"name": "c", "group": "g", **extra}]},
        )
        return checks(transport=_Transport({"/evals/checks": payload}))[0]

    def test_a_retrieval_check_says_so(self):
        found = self._one({"kind": "retrieval", "corpus": "agent"})
        assert found.kind == "retrieval" and found.corpus == "agent"

    def test_a_check_with_no_judge_is_still_judged_unless_it_says_otherwise(self):
        assert self._one({"judge": ""}).kind == "judged"

    def test_an_agent_that_omits_the_field_does_not_become_retrieval(self):
        assert self._one({"judge": "gemini-3.8-flash"}).kind == "judged"
