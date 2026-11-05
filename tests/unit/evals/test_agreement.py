"""How closely the automatic judgement matches what people decided."""

from __future__ import annotations

import pytest

from agent.src.evals.agreement import Pair, Trust, measure_agreement


def pairs(*values: tuple[bool, bool]) -> list[Pair]:
    return [
        Pair(case_id=f"c{index}", judged=judged, human=human)
        for index, (judged, human) in enumerate(values)
    ]


def test_total_agreement_is_reported_as_such():
    result = measure_agreement(pairs((True, True), (False, False)))
    assert result.agreement == 1.0


def test_total_disagreement_is_reported_as_such():
    result = measure_agreement(pairs((True, False), (False, True)))
    assert result.agreement == 0.0


def test_partial_agreement_is_a_fraction():
    result = measure_agreement(
        pairs((True, True), (True, False), (False, False), (True, True))
    )
    assert result.agreement == 0.75


def test_a_judge_that_agrees_closely_can_be_relied_on():
    result = measure_agreement(pairs(*[(True, True)] * 20))
    assert result.trust is Trust.RELIABLE


def test_a_judge_that_often_disagrees_cannot_be_relied_on():
    result = measure_agreement(pairs(*([(True, False)] * 10 + [(True, True)] * 10)))
    assert result.trust is Trust.UNRELIABLE


def test_a_judge_checked_only_a_few_times_is_not_yet_known():
    assert measure_agreement(pairs(*[(True, True)] * 5)).trust is Trust.UNKNOWN


def test_an_unknown_judge_says_how_many_more_comparisons_are_needed():
    assert "20" in measure_agreement(pairs(*[(True, True)] * 5)).reason


def test_a_judge_that_passes_what_people_fail_is_too_generous():
    result = measure_agreement(pairs(*([(True, False)] * 8 + [(True, True)] * 12)))
    assert result.bias == "too generous"


def test_a_judge_that_fails_what_people_pass_is_too_harsh():
    result = measure_agreement(pairs(*([(False, True)] * 8 + [(True, True)] * 12)))
    assert result.bias == "too harsh"


def test_a_judge_that_errs_both_ways_has_no_single_bias():
    result = measure_agreement(
        pairs(*([(True, False)] * 5 + [(False, True)] * 5 + [(True, True)] * 10))
    )
    assert result.bias == ""


def test_a_judge_in_agreement_has_no_bias():
    assert measure_agreement(pairs(*[(True, True)] * 20)).bias == ""


def test_the_cases_where_they_differed_are_named():
    result = measure_agreement(pairs((True, True), (True, False)))
    assert result.disagreements == ("c1",)


def test_the_counts_of_each_kind_of_mistake_are_reported():
    result = measure_agreement(pairs((True, False), (False, True), (True, True)))
    assert (result.too_generous, result.too_harsh) == (1, 1)


def test_an_unreliable_judge_should_not_gate_anything():
    result = measure_agreement(pairs(*([(True, False)] * 10 + [(True, True)] * 10)))
    assert result.may_gate is False


def test_a_reliable_judge_may_gate():
    assert measure_agreement(pairs(*[(True, True)] * 20)).may_gate is True


def test_an_unknown_judge_may_not_gate_either():
    assert measure_agreement(pairs(*[(True, True)] * 5)).may_gate is False


def test_comparing_nothing_is_refused():
    with pytest.raises(ValueError):
        measure_agreement([])


def test_the_same_case_twice_is_refused():
    duplicated = [
        Pair(case_id="a", judged=True, human=True),
        Pair(case_id="a", judged=False, human=False),
    ]
    with pytest.raises(ValueError):
        measure_agreement(duplicated)
